from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from handlers.common import show_main_menu
from handlers.states import ArticleFlow
from services.rag_engine import RagEngine
from utils.my_utils import is_url

router = Router()


@router.message(ArticleFlow.waiting_source, F.text)
async def article_from_text(message: Message, state: FSMContext, db: DB, rag: RagEngine, settings: Settings) -> None:
    text = (message.text or "").strip()
    user_id = message.from_user.id

    if not is_url(text):
        await message.answer("Похоже, это не ссылка. Пришли URL (http/https) или отправь PDF/TXT файл.")
        return

    await message.answer("Скачиваю и индексирую статью… Это может занять минутку.")
    try:
        title = await rag.reindex_from_url(user_id, text)
        note = f"✅ Готово! Я проиндексировал: <b>{title}</b>\nТеперь можно задавать вопросы."
        await show_main_menu(message, state, db, settings, note=note)
    except Exception as e:
        await show_main_menu(message, state, db, settings, note=f"❌ Не получилось обработать ссылку: {e}")


@router.message(ArticleFlow.waiting_source, F.document)
async def article_from_document(message: Message, state: FSMContext, db: DB, rag: RagEngine, settings: Settings, bot) -> None:
    doc = message.document
    user_id = message.from_user.id

    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await show_main_menu(
            message, state, db, settings,
            note="❌ Файл слишком большой. Telegram для ботов обычно позволяет скачивать до ~20MB."
        )
        return

    await message.answer("Скачиваю файл…")
    try:
        buf = await bot.download(doc)
        if hasattr(buf, "getvalue"):
            data = buf.getvalue()
        else:
            data = buf.read()

        await message.answer("Индексирую документ…")
        title = await rag.reindex_from_file(user_id, doc.file_name or "document", data)
        note = f"✅ Готово! Я проиндексировал: <b>{title}</b>\nТеперь можно задавать вопросы."
        await show_main_menu(message, state, db, settings, note=note)
    except Exception as e:
        await show_main_menu(message, state, db, settings, note=f"❌ Не получилось обработать файл: {e}")
