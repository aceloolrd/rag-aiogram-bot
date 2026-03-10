from __future__ import annotations

from typing import List


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """Простое разбиение текста на “чанки” с перекрытием.

    Почему так:
    - по символам — предсказуемо и без лишних зависимостей
    - overlap помогает, чтобы смысл не обрывался на границе куска
    """
    text = (text or "").strip()
    if not text:
        return []

    if chunk_size <= overlap:
        raise ValueError("chunk_size должен быть больше overlap")

    chunks: List[str] = []
    step = chunk_size - overlap

    for start in range(0, len(text), step):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

    return chunks
