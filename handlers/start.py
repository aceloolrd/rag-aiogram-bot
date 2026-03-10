from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from handlers.common import show_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: DB, settings: Settings) -> None:
    # На /start просто фиксируем пользователя в БД и показываем меню
    await db.ensure_user(message.from_user.id)

    await show_main_menu(
        message=message,
        state=state,
        db=db,
        settings=settings,
        note=(
            "Привет! Я помогу быстро разобраться со статьёй или документом.\n"
            "Сначала нажми “📄 Загрузить статью/файл”, потом задавай вопросы."
        ),
    )
