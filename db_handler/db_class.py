from __future__ import annotations

import aiosqlite
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class UserSettings:
    user_id: int
    has_article: bool
    use_custom_prompt: bool
    custom_prompt: str
    last_source: str


class DB:
    """Простой слой над SQLite.

    Мы специально держим API маленьким:
    - не плодим ORM
    - всё предсказуемо
    - миграции пока не нужны (таблица одна)
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    has_article INTEGER NOT NULL DEFAULT 0,
                    use_custom_prompt INTEGER NOT NULL DEFAULT 0,
                    custom_prompt TEXT NOT NULL DEFAULT '',
                    last_source TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            await db.commit()

    async def ensure_user(self, user_id: int) -> None:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT user_id FROM users WHERE user_id = ?",
                (user_id,),
            )
            row = await cur.fetchone()
            if row is None:
                await db.execute(
                    """
                    INSERT INTO users (user_id, has_article, use_custom_prompt, custom_prompt, last_source, created_at, updated_at)
                    VALUES (?, 0, 0, '', '', ?, ?)
                    """,
                    (user_id, now, now),
                )
            else:
                await db.execute(
                    "UPDATE users SET updated_at = ? WHERE user_id = ?",
                    (now, user_id),
                )
            await db.commit()

    async def get_user(self, user_id: int) -> UserSettings:
        await self.ensure_user(user_id)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                """
                SELECT user_id, has_article, use_custom_prompt, custom_prompt, last_source
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            )
            row = await cur.fetchone()

        assert row is not None
        return UserSettings(
            user_id=int(row[0]),
            has_article=bool(row[1]),
            use_custom_prompt=bool(row[2]),
            custom_prompt=row[3] or "",
            last_source=row[4] or "",
        )

    async def set_has_article(self, user_id: int, value: bool) -> None:
        await self.ensure_user(user_id)
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET has_article = ?, updated_at = ? WHERE user_id = ?",
                (1 if value else 0, now, user_id),
            )
            await db.commit()

    async def set_last_source(self, user_id: int, value: str) -> None:
        await self.ensure_user(user_id)
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_source = ?, updated_at = ? WHERE user_id = ?",
                (value, now, user_id),
            )
            await db.commit()

    async def set_custom_prompt(self, user_id: int, prompt: str, use_custom: bool) -> None:
        await self.ensure_user(user_id)
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users
                SET custom_prompt = ?, use_custom_prompt = ?, updated_at = ?
                WHERE user_id = ?
                """,
                (prompt, 1 if use_custom else 0, now, user_id),
            )
            await db.commit()

    async def reset_prompts(self, user_id: int) -> None:
        await self.set_custom_prompt(user_id=user_id, prompt="", use_custom=False)
