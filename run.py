from __future__ import annotations

import asyncio

from config import Settings, logger
from create_bot import create_app


async def main() -> None:
    settings = Settings.from_env()
    bot, dp, db, rag = await create_app(settings)

    # Dependency Injection: эти объекты будут доступны в хендлерах как параметры.
    await dp.start_polling(
        bot,
        db=db,
        rag=rag,
        settings=settings,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено пользователем.")
