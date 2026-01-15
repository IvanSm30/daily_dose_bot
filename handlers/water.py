from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from datetime import datetime, timezone

from states.states import WaterStates
from database import AsyncSessionLocal
from models.models import User, WaterLog

router = Router()


@router.message(Command("log_water"))
async def cmd_log_water(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    telegram_id = message.from_user.id

    # Проверяем, есть ли пользователь в БД
    async with AsyncSessionLocal() as session:
        user = await session.get(User, telegram_id)
        if not user:
            await message.answer("❌ Сначала настрой профиль: /set_profile")
            return

    if len(args) > 1 and args[1].isdigit():
        quantity = int(args[1])
        if not (50 <= quantity <= 5000):
            await message.answer("❌ Укажите объём от 50 до 5000 мл.")
            return
        await _save_water_entry(telegram_id, quantity, message)
    else:
        await message.answer("💧 Сколько воды выпили (мл)?")
        await state.set_state(WaterStates.quantity)


@router.message(WaterStates.quantity)
async def process_water_quantity(message: Message, state: FSMContext):
    telegram_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        user = await session.get(User, telegram_id)
        if not user:
            await message.answer("❌ Сначала настрой профиль: /set_profile")
            await state.clear()
            return

    text = message.text.strip()
    if not text.isdigit() or not (50 <= int(text) <= 5000):
        await message.answer("❌ Объём: 50–5000 мл")
        return

    quantity = int(text)
    await _save_water_entry(telegram_id, quantity, message)
    await state.clear()


async def _save_water_entry(telegram_id: int, quantity: int, message: Message):
    async with AsyncSessionLocal() as session:
        # Получаем пользователя
        user = await session.get(User, telegram_id)
        if not user:
            await message.answer("❌ Профиль не найден. Настройте его: /set_profile")
            return

        # Сохраняем запись
        new_log = WaterLog(telegram_id=telegram_id, quantity=quantity)
        session.add(new_log)
        await session.commit()

        # Считаем сегодняшнюю сумму
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        total_today = await session.execute(
            select(func.sum(WaterLog.quantity))
            .where(WaterLog.telegram_id == telegram_id)
            .where(WaterLog.logged_at >= today_start)
        )
        total = total_today.scalar() or 0

        water_goal = user.water_goal
        remaining = max(0, water_goal - total)
        status = (
            "✅ Вы выполнили норму!"
            if remaining == 0
            else f"💧 Осталось: {remaining} мл"
        )

        await message.answer(
            f"💧 Записано: {quantity} мл\n"
            f"📊 Всего сегодня: {total} / {water_goal} мл\n"
            f"{status}"
        )
