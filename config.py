from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("rag_bot")


@dataclass(frozen=True)
class Settings:
    # Telegram
    TELEGRAM_TOKEN: str

    # Ollama
    OLLAMA_BASE_URL: str
    OLLAMA_CHAT_MODEL: str
    OLLAMA_EMBED_MODEL: str
    OLLAMA_TIMEOUT_SEC: int

    # Optional
    REQUIRED_CHANNEL: str | None
    ADMINS: tuple[int, ...]
    WORK_TIME_START: str
    WORK_TIME_END: str

    # Paths
    DATA_DIR: Path
    DB_PATH: Path
    INDEX_DIR: Path
    TMP_DIR: Path

    # Buttons...
    BTN_UPLOAD: str = "📄 Загрузить статью/файл"
    BTN_ASK: str = "❓ Задать вопрос"
    BTN_SUMMARY: str = "🧾 Краткое резюме"
    BTN_PROMPT: str = "⚙️ Настройки промпта"
    BTN_RESET: str = "🗑️ Сбросить базу знаний"
    BTN_CANCEL: str = "❌ Отмена"

    BTN_PROMPT_DEFAULT: str = "✅ Использовать промпт по умолчанию"
    BTN_PROMPT_CUSTOM: str = "✍️ Задать свой промпт"

    @staticmethod
    def from_env() -> "Settings":
        token = os.getenv("TELEGRAM_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_TOKEN не найден в переменных окружения (.env)")

        ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
        ollama_chat_model = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:4b").strip()
        ollama_embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text").strip()
        timeout_sec = int(os.getenv("OLLAMA_TIMEOUT_SEC", "120").strip())

        admins_raw = os.getenv("ADMINS", "").strip()
        admins: tuple[int, ...] = tuple(
            int(x) for x in admins_raw.split(",") if x.strip().isdigit()
        )

        required_channel = os.getenv("REQUIRED_CHANNEL", "").strip() or None

        data_dir = Path(os.getenv("DATA_DIR", "data")).resolve()
        tmp_dir = data_dir / "tmp"
        index_dir = data_dir / "indexes"
        db_path = data_dir / "user_data.db"

        tmp_dir.mkdir(parents=True, exist_ok=True)
        index_dir.mkdir(parents=True, exist_ok=True)

        return Settings(
            TELEGRAM_TOKEN=token,
            OLLAMA_BASE_URL=ollama_base,
            OLLAMA_CHAT_MODEL=ollama_chat_model,
            OLLAMA_EMBED_MODEL=ollama_embed_model,
            OLLAMA_TIMEOUT_SEC=timeout_sec,
            REQUIRED_CHANNEL=required_channel,
            ADMINS=admins,
            WORK_TIME_START=os.getenv("WORK_TIME_START", "08:00").strip(),
            WORK_TIME_END=os.getenv("WORK_TIME_END", "23:00").strip(),
            DATA_DIR=data_dir,
            DB_PATH=db_path,
            INDEX_DIR=index_dir,
            TMP_DIR=tmp_dir,
        )


# “Человеческий” промпт, который удобно править под себя
DEFAULT_SYSTEM_PROMPT = (
    "Ты — умный и полезный помощник, который помогает людям \
быстро находить ответы в тексте. Отвечай ясно и по существу. "
    "Если в контексте нет прямого ответа — скажи об этом честно, "
    "не придумывай фактов и не уверяй, чего нет в тексте.\n\n"
    "Постарайся дать:\n"
    "1) Короткий и понятный ответ в 1–2 предложениях.\n"
    "2) Основные факты из текста, которые помогли тебе ответить.\n"
    "3) Ограничения, если данных недостаточно.\n"
    "Отвечай вежливо и по-русски.\n"
)


DEFAULT_USER_PROMPT_TEMPLATE = (
    "Контекст (фрагменты из статьи/файла):\n"
    "{context}\n\n"
    "Вопрос пользователя: {question}\n\n"
    "Не придумывай того, чего нет в тексте. Если прямого ответа нет, скажи об этом."
)
