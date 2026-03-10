from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import aiohttp
import numpy as np

from config import Settings, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_PROMPT_TEMPLATE
from db_handler.db_class import DB
from services.loaders import LoadedDocument, load_from_url, load_from_pdf_bytes, load_from_txt_bytes
from services.vector_store import VectorStore, l2_normalize
from utils.text_utils import chunk_text
from utils.my_utils import normalize_whitespace


@dataclass
class RetrievedChunk:
    text: str
    source: str
    chunk_id: int
    score: float


class RagEngine:
    def __init__(self, settings: Settings, db: DB):
        self.settings = settings
        self.db = db
        self._user_locks: dict[int, asyncio.Lock] = {}

        base = (settings.OLLAMA_BASE_URL or "").rstrip("/")
        # можно передать и с /api, и без — нормализуем
        self._ollama_api = base if base.endswith("/api") else (base + "/api")

        self._timeout = aiohttp.ClientTimeout(total=settings.OLLAMA_TIMEOUT_SEC)

    # 
    def _lock_for(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]

    def _user_index_dir(self, user_id: int) -> Path:
        return self.settings.INDEX_DIR / str(user_id)

    async def reset_index(self, user_id: int) -> None:
        folder = self._user_index_dir(user_id)
        if folder.exists():
            for p in folder.glob("*"):
                try:
                    p.unlink() # удаляем файлы
                except Exception:
                    pass 
            try:
                folder.rmdir() # удаляем папку
            except Exception:
                pass
            
        # проверим, что индекса действительно нет
        await self.db.set_has_article(user_id, False) 
        await self.db.set_last_source(user_id, "")
    
    async def reindex_from_url(self, user_id: int, url: str) -> str:
        doc = await load_from_url(url)
        await self._reindex_text(user_id, doc)
        return doc.source_title

    async def reindex_from_file(self, user_id: int, filename: str, data: bytes) -> str:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            doc = load_from_pdf_bytes(data, fallback_title=filename)
        elif lower.endswith(".txt"):
            doc = load_from_txt_bytes(data, fallback_title=filename)
        else:
            doc = load_from_txt_bytes(data, fallback_title=filename)

        await self._reindex_text(user_id, doc)
        return doc.source_title

    async def _reindex_text(self, user_id: int, doc: LoadedDocument) -> None:
        async with self._lock_for(user_id):
            text = doc.text
            max_chars = 700_000
            if len(text) > max_chars:
                text = text[:max_chars] # обрезаем до 700к

            chunks = chunk_text(text, chunk_size=1200, overlap=200) # разбиваем на чанки 
            if not chunks:
                raise ValueError("Не удалось подготовить чанки — текст пустой.")

            vectors = await self._embed_texts(chunks) # векторизуем чанки

            # Ollama /api/embed уже возвращает unit-length, но повторная нормализация не повредит
            vectors = l2_normalize(vectors) # векторы должны быть unit-length для cosine similarity

            items = [{"text": c, "source": doc.source_title, "chunk_id": i} for i, c in enumerate(chunks)]
            store = VectorStore(vectors=vectors, chunks=items)
            store.save(self._user_index_dir(user_id))

            await self.db.set_has_article(user_id, True)
            await self.db.set_last_source(user_id, doc.source_title)

    async def answer(self, user_id: int, question: str, k: int = 4) -> str:
        question = normalize_whitespace(question)
        if not question:
            return "Похоже, вопрос пустой. Напиши его текстом 🙂"

        user = await self.db.get_user(user_id)
        if not user.has_article:
            return "Сначала загрузите статью/файл (кнопка “📄 Загрузить статью/файл”)."

        store = VectorStore.load(self._user_index_dir(user_id))

        q_vec = await self._embed_texts([question])
        q_vec = l2_normalize(q_vec)[0]

        retrieved = store.search(q_vec, k=k)
        chunks = [
            RetrievedChunk(
                text=item["text"],
                source=item.get("source", ""),
                chunk_id=int(item.get("chunk_id", 0)),
                score=float(score),
            )
            for item, score in retrieved
        ]

        if not chunks:
            return "Не нашёл в базе знаний ничего похожего. Попробуй переформулировать вопрос."

        context = self._format_context(chunks)

        system_prompt = DEFAULT_SYSTEM_PROMPT
        
        if user.use_custom_prompt and user.custom_prompt.strip(): # если у пользователя есть кастомный промт
            system_prompt = user.custom_prompt.strip() # используем его

        user_prompt = DEFAULT_USER_PROMPT_TEMPLATE.format(context=context, question=question)

        return await self._chat(system_prompt=system_prompt, user_prompt=user_prompt)

    async def summarize(self, user_id: int) -> str:
        user = await self.db.get_user(user_id)
        if not user.has_article:
            return "Сначала загрузите статью/файл (кнопка “📄 Загрузить статью/файл”)."

        store = VectorStore.load(self._user_index_dir(user_id))

        take = min(6, store.size)
        chunks = [
            RetrievedChunk(
                text=store.chunks[i]["text"],
                source=store.chunks[i].get("source", ""),
                chunk_id=int(store.chunks[i].get("chunk_id", i)),
                score=1.0,
            )
            for i in range(take)
        ]
        context = self._format_context(chunks)

        system_prompt = DEFAULT_SYSTEM_PROMPT
        if user.use_custom_prompt and user.custom_prompt.strip():
            system_prompt = user.custom_prompt.strip()

        user_prompt = (
            "На основе приведённого ниже контекста сделай подробное, но краткое резюме. "
            "Включи следующие элементы:\n"
            "1) 📋 Основные идеи — ключевые тезисы и факты.\n"
            "2) ✨ Самое важное — что стоит запомнить.\n"
            "3) 📎 Дополнительные детали — если есть.\n"
            "4) 🧠 Краткий вывод — одно-два предложения о сути текста.\n\n"
            f"Контекст:\n{context}\n\n"
            "Ответь на русском, структурированно, без выдумок за пределами контекста."
        )

        return await self._chat(system_prompt=system_prompt, user_prompt=user_prompt)

    def _format_context(self, chunks: List[RetrievedChunk]) -> str:
        lines = []
        for c in chunks:
            lines.append(f"Фрагмент {c.chunk_id + 1} (релевантность ~ {c.score:.3f}):\n{c.text}")
        return "\n\n---\n\n".join(lines)

    async def _ollama_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._ollama_api}/{path.lstrip('/')}"
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(url, json=payload) as resp:
                raw = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"Ollama HTTP {resp.status}: {raw[:500]}")
                try:
                    return await resp.json()
                except Exception as e:
                    raise RuntimeError(f"Ответ Ollama не JSON: {raw[:500]}") from e

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        data = await self._ollama_post(
            "chat",
            {
                "model": self.settings.OLLAMA_CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                # stream по умолчанию true — отключаем, чтобы получить один JSON-ответ
                "stream": False,
                "options": {"temperature": 0.3},
            },
        )
        content = ((data.get("message") or {}).get("content") or "").strip()
        return content or "Не получилось сгенерировать ответ (пустой ответ модели)."

    async def _embed_texts(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        vectors: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            data = await self._ollama_post(
                "embed",
                {
                    "model": self.settings.OLLAMA_EMBED_MODEL,
                    "input": batch,  # docs: input может быть string или string[] :contentReference[oaicite:8]{index=8}
                },
            )
            emb = data.get("embeddings") or []
            if not emb:
                raise RuntimeError(f"Ollama embed вернул пусто: keys={list(data.keys())}")
            vectors.extend(emb)

        return np.array(vectors, dtype=np.float32)
