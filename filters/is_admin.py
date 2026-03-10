from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsAdminFilter(BaseFilter):
    """Фильтр на админа.

    Используем там, где надо дать доступ к “тяжёлым” действиям
    (например, массовая очистка данных или скрытые команды).
    """

    def __init__(self, admins: tuple[int, ...]):
        self.admins = set(admins)

    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id if message.from_user else 0
        return user_id in self.admins
