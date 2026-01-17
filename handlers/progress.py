from datetime import datetime, timezone
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import func, select

from models.models import FoodLog, WaterLog, WorkoutLog
from database import AsyncSessionLocal

from utils import get_user_profile

router = Router()


@router.message(Command("check_progress"))
async def cmd_check_progress(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    user = await get_user_profile(telegram_id)

    if not user:
        await message.answer("❌ Сначала настрой профиль: /set_profile")
        return

    await _progress(telegram_id, message)


# 📊 Прогресс:
# Вода:
# - Выпито: 1500 мл из 2400 мл.
# - Осталось: 900 мл.

# Калории:
# - Потреблено: 1800 ккал из 2500 ккал.
# - Сожжено: 400 ккал.
# - Баланс: 1400 ккал.


async def _progress(telegram_id: int, message: Message):
    async with AsyncSessionLocal() as session:
        user = await get_user_profile(telegram_id)

        if not user:
            await message.answer("❌ Сначала настрой профиль: /set_profile")
            return

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        total_today_water = await session.execute(
            select(func.sum(WaterLog.quantity))
            .where(WaterLog.telegram_id == telegram_id)
            .where(WaterLog.logged_at >= today_start)
        )
        total_water_today = total_today_water.scalar() or 0
        water_goal = user.water_goal
        remaining_water = max(0, water_goal - total_water_today)

        total_result_calories = await session.execute(
            select(func.sum(FoodLog.calories))
            .where(FoodLog.telegram_id == telegram_id)
            .where(FoodLog.logged_at >= today_start)
        )
        total_calories_today = total_result_calories.scalar() or 0
        calories_goal = user.calorie_goal
        remaining_calories = max(0, calories_goal - total_calories_today)

        total_result_burned_calories = await session.execute(
            select(func.sum(WorkoutLog.calories_burned))
            .where(WorkoutLog.telegram_id == telegram_id)
            .where(WorkoutLog.logged_at >= today_start)
        )
        total_burned_calories_today = total_result_burned_calories.scalar() or 0

        await message.answer(
            "📊 <b>Прогресс:</b>\n\n"
            "💧 <b>Вода</b>\n"
            f"  Выпито: {total_water_today} / {water_goal} мл\n"
            f"  Осталось: {remaining_water} мл\n\n"
            "🔥 <b>Калории</b>\n"
            f"  Потреблено: {total_calories_today} / {calories_goal + total_burned_calories_today} ккал\n"
            f"  Сожжено: {total_burned_calories_today} ккал\n"
            f"  Осталось: {remaining_calories + total_burned_calories_today} ккал"
        )
