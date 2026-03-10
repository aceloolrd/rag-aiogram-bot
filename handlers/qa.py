from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from config import Settings
from db_handler.db_class import DB
from handlers.common import show_main_menu
from handlers.states import QAFlow
from services.rag_engine import RagEngine
from utils.my_utils import split_telegram

router = Router()


@router.message(QAFlow.waiting_question, F.text)
async def handle_question(message: Message, state: FSMContext, db: DB, rag: RagEngine, settings: Settings) -> None:
    question = (message.text or "").strip()
    user_id = message.from_user.id

    await message.answer("Думаю…")
    try:
        answer = await rag.answer(user_id, question)
    except Exception as e:
        answer = f"❌ Ошибка при ответе: {e}"

    for part in split_telegram(answer):
        await message.answer(part)

    await show_main_menu(message, state, db, settings)
