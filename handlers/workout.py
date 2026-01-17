from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import func, select
from datetime import datetime, timezone

from states.states import WorkoutStates
from models.models import WaterLog, WorkoutLog
from database import AsyncSessionLocal
from utils import get_user_profile

router = Router()


def parse_workout_args(text: str):
    parts = text.strip().split()
    if len(parts) != 3:
        return None
    kind, dur_str, cal_str = parts
    try:
        duration = int(dur_str)
        calories_burned = int(cal_str)
        if duration <= 0 or calories_burned < 0:
            return None
        return kind, duration, calories_burned
    except ValueError:
        return None


@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    user = await get_user_profile(telegram_id)
    if not user:
        await message.answer("❌ Сначала настрой профиль: /set_profile")
        return

    # Проверяем, переданы ли аргументы
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        parsed = parse_workout_args(args[1])
        if parsed:
            kind, duration, calories_burned = parsed
            await _save_workout_entry(
                telegram_id=telegram_id,
                kind=kind,
                duration=duration,
                calories_burned=calories_burned,
                message=message,
            )
            return

    await message.answer("🏋️‍♂️ Введите вид тренировки (например, бег, йога):")
    await state.set_state(WorkoutStates.kind)


@router.message(WorkoutStates.kind)
async def process_kind(message: Message, state: FSMContext):
    kind = message.text.strip()
    if not kind:
        await message.answer("⚠️ Название не может быть пустым. Попробуйте снова:")
        return
    await state.update_data(kind=kind)
    await message.answer("⏱️ Продолжительность в минутах (целое число):")
    await state.set_state(WorkoutStates.duration)


@router.message(WorkoutStates.duration)
async def process_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text.strip())
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Укажите положительное целое число минут:")
        return
    await state.update_data(duration=duration)
    await message.answer("🔥 Сколько калорий потрачено? (целое число):")
    await state.set_state(WorkoutStates.calories_burned)


@router.message(WorkoutStates.calories_burned)
async def process_calorie(message: Message, state: FSMContext):
    try:
        calories_burned = int(message.text.strip())
        if calories_burned < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Калории — неотрицательное целое число:")
        return

    data = await state.get_data()
    await _save_workout_entry(
        telegram_id=message.from_user.id,
        kind=data["kind"],
        duration=data["duration"],
        calories_burned=calories_burned,
        message=message,
    )
    await state.clear()


async def _save_workout_entry(
    telegram_id: int,
    kind: str,
    duration: int,
    calories_burned: int,
    message: Message,
):
    async with AsyncSessionLocal() as session:
        user = await get_user_profile(telegram_id)
        if not user:
            await message.answer("❌ Сначала настрой профиль: /set_profile")
            return

        new_log = WorkoutLog(
            telegram_id=telegram_id,
            kind=kind,
            duration=duration,
            calories_burned=calories_burned,
        )
        session.add(new_log)
        await session.commit()

        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        total_result = await session.execute(
            select(func.sum(WorkoutLog.calories_burned))
            .where(WorkoutLog.telegram_id == telegram_id)
            .where(WorkoutLog.logged_at >= today_start)
        )
        total_burned = total_result.scalar() or 0

        quantity = duration / 30 * 200
        new_log = WaterLog(telegram_id=telegram_id, quantity=quantity)
        session.add(new_log)
        await session.commit()

        await message.answer(
            f"✅ Записано: {calories_burned} ккал ({duration} мин, {kind.lower()})\n"
            f"🔥 Сегодня потрачено: {total_burned} ккал\n"
            f"Дополнительно: добавляется 200 мл воды за каждые 30 минут."
        )
