import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
)

from config import BOT_TOKEN  # REDIS_URL

from database import init_models
from handlers import profile, progress, start, water, cancel, food, workout

from middlewares.logger import CommandLoggerMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


async def on_startup(bot: Bot):
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="set_profile", description="Настройка профиля"),
        BotCommand(command="log_water", description="Запись воды"),
        BotCommand(command="log_food", description="Запись еды"),
        BotCommand(command="log_workout", description="Запись тренировки"),
        BotCommand(command="check_progress", description="Проверка прогресса"),
        BotCommand(command="cancel", description="Отмена действия"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    await init_models()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.middleware(CommandLoggerMiddleware())

    dp.include_router(cancel.router)
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(water.router)
    dp.include_router(food.router)
    dp.include_router(workout.router)
    dp.include_router(progress.router)

    dp.startup.register(on_startup)

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
