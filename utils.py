from cachetools import TTLCache
from typing import Optional, Dict, Any
from models.models import User
from database import AsyncSessionLocal
import logging

logger = logging.getLogger("user_cache")

# Кэш: максимум 1000 пользователей, живут 10 минут (600 сек)
_user_profile_cache = TTLCache(maxsize=1000, ttl=600)


async def get_user_profile(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает словарь с профилем пользователя или None, если не найден."""
    if telegram_id in _user_profile_cache:
        logger.debug(f"✅ Кэш hit для пользователя {telegram_id}")
        return _user_profile_cache[telegram_id]

    logger.debug(f"🔍 Кэш miss для пользователя {telegram_id} — читаем из БД")
    async with AsyncSessionLocal() as session:
        user = await session.get(User, telegram_id)
        if not user:
            return None

        _user_profile_cache[telegram_id] = user
        return user


def invalidate_user_cache(telegram_id: int) -> None:
    """Удаляет профиль из кэша (вызывать после обновления профиля)."""
    if telegram_id in _user_profile_cache:
        del _user_profile_cache[telegram_id]
        logger.debug(f"🧹 Кэш инвалидирован для пользователя {telegram_id}")
