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


async def on_startup(bot: Bot):
    commands = [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="set_profile", description="Настройка профиля"),
        BotCommand(command="log_water", description="Запись воды"),
        BotCommand(command="log_food", description="Запись еды"),
        BotCommand(command="log_workout", description="Запись тренировки"),
        BotCommand(command="check_progress", description="Проверка прогресса"),
        BotCommand(command="cancel", description="Отмена действия")
    ]
    await bot.set_my_commands(commands)


# commands:

# /set_profile
# Вес (в кг), рост (в см) и возраст.
# Уровень активности (минуты в день).
# Город (для получения температуры).
# Цель калорий (по умолчанию рассчитывается, но можно задавать вручную).
# Любые параметры по вашему усмотрению.


# /log_water <количество>
# Сохраняет, сколько воды выпито.
# Показывает, сколько осталось до выполнения нормы.


# /log_food <название продукта>
# Бот использует API (например, OpenFoodFacts) для получения информации о продукте или иной подход.
# Сохраняет калорийность.


# /log_workout <тип тренировки> <время (мин)>
# Фиксирует сожжённые калории.
# Учитывает расход воды на тренировке (дополнительные 200 мл за каждые 30 минут) или более умный учет разных типов тренировок.


# /check_progress
# Показывает, сколько воды и калорий потреблено, сожжено и сколько осталось до выполнения цели.


async def main() -> None:
    await init_models()
    # storage = RedisStorage.from_url(REDIS_URL)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

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
