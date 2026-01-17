import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Dict, Any, Awaitable

logger = logging.getLogger("commands")


class CommandLoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.chat.type == "private":
            user = event.from_user
            text = event.text or event.caption or ""
            if text.startswith("/"):
                logger.info(f"User @{user.username} ({user.id}) executed: {text!r}")
        return await handler(event, data)
