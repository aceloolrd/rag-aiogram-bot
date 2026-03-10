from __future__ import annotations

import re
from pathlib import Path
from typing import List

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_url(text: str) -> bool:
    return bool(_URL_RE.match((text or "").strip()))


def normalize_whitespace(text: str) -> str:
    # Делаем текст читабельным: убираем лишние пробелы и пустые строки
    text = (text or "").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_delete(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        # Не падаем из-за мусора в temp — пусть лучше останется, чем упадёт бот
        pass


def split_telegram(text: str, max_len: int = 3800) -> List[str]:
    """Telegram режет сообщения по лимиту, поэтому мы аккуратно бьём длинные ответы.

    4096 — технический лимит, но оставим запас под HTML-теги.
    """
    text = text or ""
    if len(text) <= max_len:
        return [text]

    parts: List[str] = []
    buf = ""

    for paragraph in text.split("\n"):
        candidate = (buf + "\n" + paragraph).strip() if buf else paragraph
        if len(candidate) <= max_len:
            buf = candidate
            continue

        if buf:
            parts.append(buf)
            buf = ""

        # Если абзац всё равно слишком большой — режем “в лоб”
        while len(paragraph) > max_len:
            parts.append(paragraph[:max_len])
            paragraph = paragraph[max_len:]
        buf = paragraph

    if buf:
        parts.append(buf)

    return parts
