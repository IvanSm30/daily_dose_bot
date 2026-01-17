# handlers/graphs.py
from aiogram import Router
from aiogram.types import Message, InputFile
from aiogram.filters import Command
from services.graphic import generate_water_graph, generate_calories_graph
from utils import get_user_profile

router = Router()


@router.message(Command("show_graphic"))
async def cmd_show_graph(message: Message):
    telegram_id = message.from_user.id

    user = await get_user_profile(telegram_id)
    if not user:
        await message.answer("❌ Сначала настрой профиль: /set_profile")
        return

    water_img = await generate_water_graph(telegram_id)
    calories_img = await generate_calories_graph(telegram_id)

    if not water_img and not calories_img:
        await message.answer("📉 Нет данных за последние 7 дней.")
        return

    if water_img:
        await message.answer_photo(
            InputFile(water_img), caption="💧 Ваш прогресс по воде"
        )
    if calories_img:
        await message.answer_photo(
            InputFile(calories_img), caption="🔥 Ваш прогресс по калориям"
        )
