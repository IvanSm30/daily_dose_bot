from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from datetime import datetime, timezone

from states.states import WaterStates
from database import AsyncSessionLocal
from models.models import WorkoutLog
from utils import get_user_profile

router = Router()


@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message, state: FSMContext):
    args = message.text.split(maxsplit=1)
    telegram_id = message.from_user.id

    user = await get_user_profile(telegram_id)

    if not user:
        await message.answer("❌ Сначала настрой профиль: /set_profile")
        return
