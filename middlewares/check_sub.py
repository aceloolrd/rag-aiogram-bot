from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatMemberStatus
from aiogram.types import Message

from config import Settings


class CheckSubMiddleware(BaseMiddleware):
    """Проверка подписки на канал (опционально).

    Если REQUIRED_CHANNEL не задан — ничего не проверяем.
    Если задан — вежливо просим подписаться и не пропускаем событие дальше.
    """

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        # Срабатываем только для сообщений
        if not isinstance(event, Message):
            return await handler(event, data)

        channel = self.settings.REQUIRED_CHANNEL
        if not channel:
            return await handler(event, data)

        bot = data["bot"]

        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=event.from_user.id)
            ok = member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
        except Exception:
            # Если Telegram не дал проверить (не админ в канале, приватный канал и т.п.) —
            # лучше не блокировать пользователю доступ “в никуда”.
            ok = True

        if not ok:
            await event.answer("Чтобы пользоваться ботом, подпишись на канал и попробуй снова.")
            return None

        return await handler(event, data)
