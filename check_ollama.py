from __future__ import annotations

import json
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from dotenv import load_dotenv
import os

# Этот скрипт проверяет:
# - Жив ли сервер Ollama
# - Есть ли нужные модели локально (через /api/tags)
# - Работает ли OpenAI-совместимый API (чат и эмбеддинги)

load_dotenv()


def _http_json(method: str, url: str, payload: dict | None = None, timeout: int = 60) -> dict:
    """Минимальный HTTP-клиент на стандартной библиотеке.

    Не тянем requests/httpx специально, чтобы скрипт запускался "везде",
    где есть Python + твой venv.
    """
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, data=data, method=method.upper(), headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _derive_ollama_host(openai_base_url: str) -> str:
    """
    Из OPENAI_BASE_URL вида:
      http://127.0.0.1:11434/v1/
    получаем:
      http://127.0.0.1:11434
    """
    if not openai_base_url:
        return "http://127.0.0.1:11434"

    u = urlparse(openai_base_url)
    scheme = u.scheme or "http"
    netloc = u.netloc or "127.0.0.1:11434"
    return f"{scheme}://{netloc}"


def main() -> int:
    base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1/").strip()
    # на всякий случай нормализуем
    if not base_url.endswith("/"):
        base_url += "/"

    chat_model = os.getenv("OPENAI_CHAT_MODEL", "").strip()
    embed_model = os.getenv("OPENAI_EMBED_MODEL", "").strip()

    if not chat_model or not embed_model:
        print("❌ В .env не заданы OPENAI_CHAT_MODEL и/или OPENAI_EMBED_MODEL")
        return 2

    ollama_host = _derive_ollama_host(base_url)

    print("=== Проверка Ollama ===")
    print(f"OPENAI_BASE_URL: {base_url}")
    print(f"Ollama host:     {ollama_host}")
    print(f"Chat model:      {chat_model}")
    print(f"Embed model:     {embed_model}")
    print()

    # 1) /api/tags — список локальных моделей (это самый быстрый способ понять, что “модели вообще есть”)
    # Документация: GET /api/tags :contentReference[oaicite:3]{index=3}
    try:
        tags = _http_json("GET", f"{ollama_host}/api/tags", timeout=10)
        names = [m.get("name", "") for m in tags.get("models", [])]
        names = [n for n in names if n]

        print("✅ Сервер отвечает на /api/tags")
        if names:
            print(f"Найдено локальных моделей: {len(names)}")
            # покажем первые 20, чтобы не спамить
            for n in names[:20]:
                print(" -", n)
            if len(names) > 20:
                print(f"   ... и ещё {len(names) - 20}")
        else:
            print("⚠️ Моделей не найдено (models=[]). Возможно, ты ещё ничего не делал 'ollama pull ...'.")

        # Проверим, есть ли нужные модели в списке
        missing = []
        if chat_model not in names:
            missing.append(chat_model)
        if embed_model not in names:
            missing.append(embed_model)

        if missing:
            print()
            print("⚠️ ВНИМАНИЕ: этих моделей нет локально:")
            for m in missing:
                print(" -", m)
            print("Скорее всего нужно выполнить:")
            print(f"  ollama pull {chat_model}")
            print(f"  ollama pull {embed_model}")

        print()

    except (URLError, HTTPError) as e:
        print(f"❌ Не могу достучаться до Ollama по /api/tags: {e}")
        print("   Убедись, что Ollama запущена и слушает порт 11434.")
        return 3
    except Exception as e:
        print(f"❌ Неожиданная ошибка при /api/tags: {e}")
        return 4

    # 2) Проверка OpenAI-совместимого чата: POST /v1/chat/completions :contentReference[oaicite:4]{index=4}
    print("=== Проверка OpenAI-совместимого чата (/v1/chat/completions) ===")
    try:
        t0 = time.time()
        chat_resp = _http_json(
            "POST",
            f"{base_url}chat/completions",
            payload={
                "model": chat_model,
                "messages": [{"role": "user", "content": "Ответь одним коротким словом: 'Ок'."}],
                "temperature": 0.0,
                "max_tokens": 10,
            },
            # первый прогрев модели может быть не мгновенным
            timeout=120,
        )
        dt = time.time() - t0

        # В ответе по OpenAI-формату обычно есть choices[0].message.content
        content = ""
        try:
            content = chat_resp["choices"][0]["message"]["content"]
        except Exception:
            content = str(chat_resp)[:300]

        print(f"✅ Чат работает (время: {dt:.1f} сек)")
        print("Ответ модели:", content.strip())
        print()

    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        print(f"❌ Чат вернул HTTP {e.code}")
        if body:
            print("Ответ сервера:", body[:600])
        print("Частые причины:")
        print(" - модель не скачана (ollama pull ...)")
        print(" - неверное имя модели")
        return 5
    except URLError as e:
        print(f"❌ Ошибка соединения в чате: {e}")
        return 6
    except Exception as e:
        print(f"❌ Неожиданная ошибка в чате: {e}")
        return 7

    # 3) Проверка эмбеддингов: POST /v1/embeddings :contentReference[oaicite:5]{index=5}
    print("=== Проверка эмбеддингов (/v1/embeddings) ===")
    try:
        t0 = time.time()
        emb_resp = _http_json(
            "POST",
            f"{base_url}embeddings",
            payload={
                "model": embed_model,
                "input": ["привет", "проверка эмбеддингов"],
            },
            timeout=120,
        )
        dt = time.time() - t0

        # Обычно emb_resp.data[0].embedding — список чисел
        dim = None
        try:
            vec0 = emb_resp["data"][0]["embedding"]
            dim = len(vec0)
        except Exception:
            pass

        print(f"✅ Эмбеддинги работают (время: {dt:.1f} сек)")
        if dim is not None:
            print(f"Размерность эмбеддинга: {dim}")
        else:
            print("Ответ сервера (обрезано):", str(emb_resp)[:400])
        print()

    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        print(f"❌ Эмбеддинги вернули HTTP {e.code}")
        if body:
            print("Ответ сервера:", body[:600])
        print("Частые причины:")
        print(" - embedding-модель не скачана (ollama pull nomic-embed-text)")
        print(" - Ollama слишком старая / не поддерживает модель")
        return 8
    except URLError as e:
        print(f"❌ Ошибка соединения в эмбеддингах: {e}")
        return 9
    except Exception as e:
        print(f"❌ Неожиданная ошибка в эмбеддингах: {e}")
        return 10

    print("🎉 Всё отлично: Ollama, чат и эмбеддинги работают.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
