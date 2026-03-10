from __future__ import annotations

from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from handlers.common import show_main_menu
from handlers.states import MainMenu, ArticleFlow, QAFlow, PromptFlow
from keyboards.all_keyboards import cancel_kb, prompt_menu_kb
from services.rag_engine import RagEngine
from utils.my_utils import split_telegram

router = Router()


@router.message(MainMenu.waiting_choice)
async def main_menu(message: Message, state: FSMContext, db: DB, rag: RagEngine, settings: Settings) -> None:
    text = (message.text or "").strip()
    user_id = message.from_user.id
    user = await db.get_user(user_id)

    if text == settings.BTN_UPLOAD:
        await state.set_state(ArticleFlow.waiting_source)
        await message.answer(
            "Пришли ссылку на статью (http/https) или отправь файл PDF/TXT.",
            reply_markup=cancel_kb(settings),
        )
        return

    if text == settings.BTN_ASK:
        if not user.has_article:
            await show_main_menu(message, state, db, settings, note="Сначала загрузите статью/файл.")
            return

        await state.set_state(QAFlow.waiting_question)
        await message.answer(
            "Напиши вопрос по загруженному документу.",
            reply_markup=cancel_kb(settings),
        )
        return

    if text == settings.BTN_SUMMARY:
        if not user.has_article:
            await show_main_menu(message, state, db, settings, note="Сначала загрузите статью/файл.")
            return

        await message.answer("Готовлю резюме…")
        try:
            result = await rag.summarize(user_id)
        except Exception as e:
            result = f"❌ Ошибка при резюмировании: {e}"

        for part in split_telegram(result):
            await message.answer(part)

        await show_main_menu(message, state, db, settings)
        return

    if text == settings.BTN_PROMPT:
        await state.set_state(PromptFlow.waiting_choice)
        await message.answer(
            "Настройки промпта: что выбираем?",
            reply_markup=prompt_menu_kb(settings),
        )
        return

    if text == settings.BTN_RESET:
        await message.answer("Сбрасываю базу знаний…")
        await rag.reset_index(user_id)
        await show_main_menu(message, state, db, settings, note="Готово: база знаний очищена.")
        return

    # Если пользователь набрал что-то “мимо кассы” — просто покажем меню снова.
    await show_main_menu(message, state, db, settings, note="Не понял выбор. Нажми кнопку в меню 🙂")
