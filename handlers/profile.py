from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from services.weather import get_temperature
from states.states import ProfileStates
from models.models import User
from database import AsyncSessionLocal
import re

from utils import invalidate_user_cache

router = Router()


def calculate_goals(
    weight: int, height: int, age: int, activity_minutes: int, city_temp: float = 20
) -> tuple[int, int]:
    """Точные формулы из ТЗ"""

    calorie_base = 10 * weight + 6.25 * height - 5 * age

    if activity_minutes < 30:
        factor = 1.2
    elif activity_minutes < 60:
        factor = 1.375
    elif activity_minutes < 120:
        factor = 1.55
    else:
        factor = 1.725

    calorie_goal = int(calorie_base * factor)

    water_base = weight * 30
    water_activity = (activity_minutes // 30) * 500
    water_weather = 750 if city_temp > 25 else 0

    water_goal = water_base + water_activity + water_weather

    return (
        calorie_goal,
        water_goal,
        calorie_base,
        water_base,
        water_activity,
        water_weather,
        factor,
    )


async def get_user_from_db(telegram_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def save_user_to_db(user_data: dict, message: Message):
    async with AsyncSessionLocal() as session:
        telegram_id = user_data["telegram_id"]
        existing = await session.get(User, telegram_id)
        if existing:
            # Обновляем
            for key, value in user_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            # Создаём нового
            new_user = User(**user_data)
            session.add(new_user)
        await session.commit()
        invalidate_user_cache(message.from_user.id)


@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    # Проверяем наличие в БД
    user_in_db = await get_user_from_db(telegram_id)

    if user_in_db:
        gender_display = (
            "Мужчина" if user_in_db.gender in ["мужчина", "м"] else "Женщина"
        )
        await message.answer(
            "✅ <b>Ваш профиль уже настроен:</b>\n\n"
            f"👤 <b>{gender_display}</b>\n"
            f"📏 {user_in_db.weight} кг, {user_in_db.height} см, {user_in_db.age} лет\n"
            f"🏙️ {user_in_db.city}, {user_in_db.activity_minutes} мин/день\n\n"
            f"🔥 <b>Калории:</b> {user_in_db.calorie_goal} ккал\n"
            f"💧 <b>Вода:</b> {user_in_db.water_goal} мл\n\n"
            "🔄 Хотите обновить профиль? Начнём с веса.\n"
            "Введите новый вес (кг) или отправьте /cancel для отмены."
        )
        await state.set_state(ProfileStates.weight)
    else:
        await message.answer("👤 <b>Настройка профиля</b>\n\n📊 Введите вес (кг):")
        await state.set_state(ProfileStates.weight)


@router.message(ProfileStates.weight)
async def process_weight(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (30 <= int(text) <= 300):
        await message.answer("❌ Вес: 30-300 кг")
        return
    await state.update_data(weight=int(text))
    await message.answer("📏 Рост (см):")
    await state.set_state(ProfileStates.height)


@router.message(ProfileStates.height)
async def process_height(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (100 <= int(text) <= 250):
        await message.answer("❌ Рост: 100-250 см")
        return
    await state.update_data(height=int(text))
    await message.answer("🎂 Возраст (лет):")
    await state.set_state(ProfileStates.age)


@router.message(ProfileStates.age)
async def process_age(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (10 <= int(text) <= 120):
        await message.answer("❌ Возраст: 10-120 лет")
        return
    await state.update_data(age=int(text))
    await message.answer("🏙️ Город проживания:")
    await state.set_state(ProfileStates.city)


@router.message(ProfileStates.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) < 2 or len(city) > 50 or not re.match(r"^[а-яА-Яa-zA-Z\s\-]+$", city):
        await message.answer("❌ Город (2-50 символов, только буквы):")
        return
    await state.update_data(city=city)
    await message.answer("👨‍🦰 Пол (мужчина/женщина):")
    await state.set_state(ProfileStates.gender)


@router.message(ProfileStates.gender)
async def process_gender(message: Message, state: FSMContext):
    gender = message.text.strip().lower()
    if gender not in ["мужчина", "женщина", "м", "ж"]:
        await message.answer("❌ Введите: мужчина или женщина")
        return
    await state.update_data(gender=gender)
    await message.answer("⚡ Активность (мин/день, 0-1440):")
    await state.set_state(ProfileStates.activity_minutes)


@router.message(ProfileStates.activity_minutes)
async def process_activity(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or not (0 <= int(text) <= 1440):
        await message.answer("❌ Активность: 0-1440 минут")
        return

    data = await state.get_data()
    activity_minutes = int(text)
    
    city_temp = None
    if data["city"]:
        city_temp = await get_temperature(data["city"])

    (
        calorie_goal,
        water_goal,
        calorie_base,
        water_base,
        water_activity,
        water_weather,
        factor,
    ) = calculate_goals(
        weight=data["weight"],
        height=data["height"],
        age=data["age"],
        activity_minutes=activity_minutes,
        city_temp=city_temp
    )

    await state.update_data(
        activity_minutes=activity_minutes,
        calorie_goal=calorie_goal,
        water_goal=water_goal,
        calorie_base=calorie_base,
        water_base=water_base,
    )

    await message.answer(
        f"📊 <b>Расчёт дневных норм:</b>\n\n"
        f"🔥 <b>Калории:</b>\n"
        f"   <code>10×{data['weight']} + 6.25×{data['height']} - 5×{data['age']}</code>\n"
        f"   = {calorie_base} × <b>{factor}</b> (активность)\n"
        f"   <b>{calorie_goal} ккал/день</b>\n\n"
        f"💧 <b>Вода:</b>\n"
        f"   <code>{data['weight']}×30</code> = {water_base} мл (база)\n"
        f"   +{water_activity} мл (активность)\n"
        f"   +{water_weather} мл (погода >25°C)\n"
        f"   <b>{water_goal} мл/день</b>\n\n"
        f"<i>Изменить калории? (число или 'пропустить')</i>"
    )
    await state.set_state(ProfileStates.calorie_goal)


@router.message(ProfileStates.calorie_goal)
async def process_calorie_goal(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    data = await state.get_data()

    if text == "пропустить":
        goal = data["calorie_goal"]
    elif text.isdigit() and 500 <= int(text) <= 10000:
        goal = int(text)
    else:
        await message.answer("❌ Калории: 500-10000 или 'пропустить'")
        return

    await state.update_data(calorie_goal=goal)

    await message.answer(
        f"💧 <b>Вода:</b> {data['water_goal']} мл/день\n"
        f"<i>Изменить? (число или 'пропустить')</i>"
    )
    await state.set_state(ProfileStates.water_goal)


@router.message(ProfileStates.water_goal)
async def process_water_goal(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    data = await state.get_data()

    if text == "пропустить":
        water_goal = data["water_goal"]
    elif text.isdigit() and 200 <= int(text) <= 10000:
        water_goal = int(text)
    else:
        await message.answer("❌ Вода: 200-10000 мл или 'пропустить'")
        return

    telegram_id = message.from_user.id

    # Подготавливаем данные для сохранения в БД
    user_data = {
        "telegram_id": telegram_id,
        "weight": data["weight"],
        "height": data["height"],
        "age": data["age"],
        "gender": data["gender"],
        "city": data["city"],
        "activity_minutes": data["activity_minutes"],
        "calorie_goal": data["calorie_goal"],
        "water_goal": water_goal,
    }

    try:
        await save_user_to_db(user_data, message)
    except Exception as e:
        await message.answer("⚠️ Ошибка сохранения профиля. Попробуйте позже.")
        print(f"DB Error: {e}")
        return

    gender_display = "Мужчина" if data["gender"] in ["мужчина", "м"] else "Женщина"

    await message.answer(
        "✅ <b>Профиль сохранён в базе данных!</b>\n\n"
        f"👤 <b>{gender_display}</b>\n"
        f"📏 {data['weight']} кг, {data['height']} см, {data['age']} лет\n"
        f"🏙️ {data['city']}, {data['activity_minutes']} мин/день\n\n"
        f"🔥 <b>Калории:</b> {data['calorie_goal']} ккал\n"
        f"💧 <b>Вода:</b> {water_goal} мл",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()
