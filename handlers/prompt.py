from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from handlers.common import show_main_menu
from handlers.states import PromptFlow
from keyboards.all_keyboards import cancel_kb

router = Router()


@router.message(PromptFlow.waiting_choice, F.text)
async def prompt_menu(message: Message, state: FSMContext, db: DB, settings: Settings) -> None:
    choice = (message.text or "").strip()
    user_id = message.from_user.id

    if choice == settings.BTN_PROMPT_DEFAULT:
        await db.set_custom_prompt(user_id, prompt="", use_custom=False)
        await show_main_menu(message, state, db, settings, note="✅ Ок, использую промпт по умолчанию.")
        return

    if choice == settings.BTN_PROMPT_CUSTOM:
        await state.set_state(PromptFlow.waiting_custom_prompt)
        await message.answer(
            "Пришли свой промпт (это будет <b>system</b>-сообщение для модели).\n\n"
            "Совет: попроси формат ответа, стиль, ограничения, но не забывай, что ответы должны опираться на контекст.",
            reply_markup=cancel_kb(settings),
        )
        return

    await show_main_menu(message, state, db, settings, note="Нажми кнопку в меню промпта 🙂")


@router.message(PromptFlow.waiting_custom_prompt, F.text)
async def prompt_custom_set(message: Message, state: FSMContext, db: DB, settings: Settings) -> None:
    prompt = (message.text or "").strip()
    user_id = message.from_user.id

    if len(prompt) < 20:
        await message.answer("Промпт выглядит слишком коротким. Пришли текст подлиннее (или нажми Отмена).")
        return

    await db.set_custom_prompt(user_id, prompt=prompt, use_custom=True)
    await show_main_menu(message, state, db, settings, note="✅ Сохранил! Теперь отвечаю с учётом твоего промпта.")
