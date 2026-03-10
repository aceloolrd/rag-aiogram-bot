from __future__ import annotations

from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from keyboards.all_keyboards import main_menu_kb
from handlers.states import MainMenu


async def show_main_menu(message: Message, state: FSMContext, db: DB, settings: Settings, note: str | None = None) -> None:
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    text = "Выберите действие:"
    if user.last_source:
        text += f"\n\n<b>Текущий источник:</b> {user.last_source}"

    if note:
        text = note + "\n\n" + text

    await state.set_state(MainMenu.waiting_choice)
    await message.answer(text, reply_markup=main_menu_kb(settings, has_article=user.has_article))
