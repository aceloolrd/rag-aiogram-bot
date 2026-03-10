from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from config import Settings
from work_time.time_func import WorkTimeWindow


class WorkTimeMiddleware(BaseMiddleware):
    """Ограничение по времени работы (опционально).

    Реально полезно, когда:
    - хочешь “выключать” бота ночью
    - или экономить токены/лимиты
    """

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.window = WorkTimeWindow.from_strings(settings.WORK_TIME_START, settings.WORK_TIME_END)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else 0

        # Админам — можно всегда (удобно для тестов)
        if user_id in set(self.settings.ADMINS):
            return await handler(event, data)

        if not self.window.is_now_allowed():
            await event.answer("Сейчас бот “спит”. Попробуй позже 🙂")
            return None

        return await handler(event, data)
