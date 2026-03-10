from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from handlers.common import show_main_menu

router = Router()

# Ловим отмену в любом состоянии.
# Важно: этот роутер подключаем ПЕРВЫМ (см. create_bot.py),
# чтобы “Отмена” не улетала в другие хендлеры.
@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cancel_anywhere(message: Message, state: FSMContext, db: DB, settings: Settings) -> None:
    await show_main_menu(message, state, db, settings, note="Ок, отменил.")
