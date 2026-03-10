from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import Settings, logger
from db_handler.db_class import DB
from handlers import (
    cancel_router,
    start_router,
    menu_router,
    article_router,
    qa_router,
    prompt_router,
)
from middlewares.check_sub import CheckSubMiddleware
from middlewares.work_time import WorkTimeMiddleware
from services.rag_engine import RagEngine


async def create_app(settings: Settings):
    """Создаём Bot + Dispatcher и все зависимости.

    Возвращаем кортеж (bot, dp, db, rag), чтобы run.py мог стартовать polling.
    """
    bot = Bot(
        token=settings.TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM хранится в памяти. Для продакшена с несколькими инстансами лучше Redis.
    dp = Dispatcher(storage=MemoryStorage())

    # База
    db = DB(settings.DB_PATH)
    await db.init()

    rag = RagEngine(settings=settings, db=db)

    # Middleware: порядок важен
    dp.message.middleware(WorkTimeMiddleware(settings))
    dp.message.middleware(CheckSubMiddleware(settings))

    # Роутеры
    # cancel_router — первым, чтобы "Отмена" работала везде
    dp.include_router(cancel_router)
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(article_router)
    dp.include_router(qa_router)
    dp.include_router(prompt_router)

    logger.info("Бот собран: роутеры подключены, DB готова, RAG engine готов.")
    return bot, dp, db, rag
