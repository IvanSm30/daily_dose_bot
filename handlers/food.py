import aiohttp
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from datetime import datetime, timezone
from sqlalchemy import func, select
from states.states import FoodStates
from models.models import FoodLog
from database import AsyncSessionLocal

import json
import logging

from utils import get_user_profile

router = Router()

# Кэш для продуктов (опционально, чтобы не спамить API)
_product_cache = {}

# Настройка логгера (можно использовать общий)
logger = logging.getLogger("food_api")


async def search_openfoodfacts(product_name: str) -> dict | None:
    """Ищет продукт в OpenFoodFacts с фокусом на Россию + подробное логирование"""
    if product_name in _product_cache:
        return _product_cache[product_name]

    url = "https://world.openfoodfacts.org/cgi/search.pl"

    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "json": 1,
        "page_size": 5,
        "tagtype_0": "countries",
        "tag_contains_0": "russia",
        "sort_by": "unique_scans_n",
    }

    logger.info(f"🔍 Запрос к OpenFoodFacts: {product_name}")
    logger.debug(f"URL: {url}")
    logger.debug(f"Params: {params}")

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                logger.info(f"📡 Ответ от OpenFoodFacts: статус {response.status}")

                if response.status != 200:
                    logger.warning(f"❌ Некорректный статус: {response.status}")
                    return None

                try:
                    text = await response.text()
                    # Логируем первые 500 символов тела (осторожно: может быть большим)
                    logger.debug(f"📄 Тело ответа (первые 500 симв): {text[:500]}...")
                    data = json.loads(text)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Ошибка парсинга JSON: {e}")
                    logger.debug(f"Полный ответ: {text[:1000]}")
                    return None

                products = data.get("products", [])
                logger.info(f"📦 Найдено продуктов: {len(products)}")

                if not products:
                    # Fallback: глобальный поиск
                    logger.info("🔄 Попытка глобального поиска (без фильтра России)")
                    fallback_params = {
                        "search_terms": product_name,
                        "search_simple": 1,
                        "json": 1,
                        "page_size": 1,
                    }
                    async with session.get(url, params=fallback_params) as resp2:
                        logger.info(f"📡 Fallback-ответ: статус {resp2.status}")
                        if resp2.status == 200:
                            try:
                                fallback_data = await resp2.json()
                                products = fallback_data.get("products", [])
                                logger.info(
                                    f"📦 Fallback: найдено {len(products)} продуктов"
                                )
                            except Exception as e2:
                                logger.error(f"❌ Ошибка fallback-парсинга: {e2}")
                        else:
                            logger.warning(f"❌ Fallback вернул статус {resp2.status}")

                for i, product in enumerate(products):
                    name = (
                        product.get("product_name_ru")
                        or product.get("product_name")
                        or ""
                    ).strip()

                    nutriments = product.get("nutriments", {})
                    energy_kcal = nutriments.get("energy-kcal_100g")

                    if energy_kcal is None:
                        energy_kcal = nutriments.get("energy_100g")
                        if energy_kcal:
                            energy_kcal = round(energy_kcal / 4.184)

                    logger.debug(f"  [{i}] {name} → {energy_kcal} ккал/100г")

                    if name and energy_kcal and energy_kcal > 0:
                        result = {"name": name, "calories_per_100g": int(energy_kcal)}
                        _product_cache[product_name] = result
                        logger.info(f"✅ Найден продукт: {result}")
                        return result

                logger.warning("❌ Подходящих продуктов с калориями не найдено")
                return None

    except aiohttp.ClientError as e:
        logger.error(f"🌐 Ошибка сети при запросе к OpenFoodFacts: {e}")
        return None
    except Exception as e:
        logger.exception(f"💥 Неожиданная ошибка в search_openfoodfacts: {e}")
        return None


@router.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    telegram_id = message.from_user.id

    # Проверка профиля
    profile = await get_user_profile(telegram_id)

    if not profile:
        await message.answer("❌ Сначала настрой профиль: /set_profile")
        return

    if len(args) > 1:
        product_name = args[1].strip()
        food_info = await search_openfoodfacts(product_name)
        if not food_info:
            await message.answer(
                f"❌ Не удалось найти продукт «{product_name}».\n"
                "Попробуйте другое название или отправьте /cancel."
            )
            return

        await state.update_data(
            name=food_info["name"],
            calories_per_100g=food_info["calories_per_100g"],
        )
        await message.answer(
            f"🍌 <b>{food_info['name']}</b> — {food_info['calories_per_100g']} ккал на 100 г.\n"
            "Сколько грамм вы съели?"
        )
        await state.set_state(FoodStates.weight)
    else:
        await message.answer("🍽️ Введите название продукта:")
        await state.set_state(FoodStates.name)


@router.message(FoodStates.name)
async def process_food_name(message: Message, state: FSMContext):
    product_name = message.text.strip()
    food_info = await search_openfoodfacts(product_name)

    if not food_info:
        await message.answer(
            f"❌ Не удалось найти продукт «{product_name}».\n"
            "Попробуйте другое название:"
        )
        return

    await state.update_data(
        name=food_info["name"], calories_per_100g=food_info["calories_per_100g"]
    )
    await message.answer(
        f"🍽️ <b>{food_info['name']}</b> — {food_info['calories_per_100g']} ккал на 100 г.\n"
        "Сколько грамм вы съели?"
    )
    await state.set_state(FoodStates.weight)


@router.message(FoodStates.weight)
async def process_food_weight(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (10 <= int(text) <= 5000):
        await message.answer("❌ Укажите вес от 10 до 5000 грамм.")
        return

    weight = int(text)
    data = await state.get_data()
    name = data["name"]
    calories_per_100g = data["calories_per_100g"]
    total_calories = round(calories_per_100g * weight / 100)

    await _save_food_entry(
        telegram_id=message.from_user.id,
        name=name,
        weight=weight,
        calories=total_calories,
        message=message,
    )
    await state.clear()


async def _save_food_entry(
    telegram_id: int,
    name: str,
    weight: int,
    calories: int,
    message: Message,
):
    async with AsyncSessionLocal() as session:
        user = await get_user_profile(telegram_id)

        if not user:
            await message.answer("❌ Сначала настрой профиль: /set_profile")
            return

        new_log = FoodLog(
            telegram_id=telegram_id,
            name=name,
            weight=weight,
            calories=calories,
        )
        session.add(new_log)
        await session.commit()

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        total_result = await session.execute(
            select(func.sum(FoodLog.calories))
            .where(FoodLog.telegram_id == telegram_id)
            .where(FoodLog.logged_at >= today_start)
        )
        total_calories_today = total_result.scalar() or 0

        # Считаем остаток
        goal = user.calorie_goal
        remaining = max(0, goal - total_calories_today)
        status = (
            "✅ Вы уложились в норму!"
            if remaining == 0
            else f"📉 Осталось: {remaining} ккал"
        )

        await message.answer(
            f"✅ Записано: {calories} ккал ({weight} г {name.lower()})\n"
            f"📊 Сегодня: {total_calories_today} / {goal} ккал\n"
            f"{status}"
        )
