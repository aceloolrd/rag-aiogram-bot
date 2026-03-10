# RAG Aiogram Bot

![Python](https://img.shields.io/badge/python-3.10+-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.22-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A Telegram bot for building personal knowledge bases from documents and querying them with a local LLM — no cloud API required.

---

*Телеграм-бот для создания персональных баз знаний из документов и запросов к ним через локальную языковую модель — без облачных API.*

---

## Features

- **Document ingestion:** URLs (web scraping), PDF files, plain text
- **Semantic search:** NumPy-based vector store with cosine similarity (no external vector DB)
- **Local inference:** Ollama for both embeddings and chat — fully offline
- **Per-user isolation:** each user has their own index and settings stored in SQLite
- **Custom prompts:** users can override the system prompt for answers
- **Optional guards:** channel subscription check, working hours enforcement, admin filter

## Architecture

```
Document → loader → chunk (1200 chars / 200 overlap)
         → embed (Ollama /api/embed) → vectors.npy + chunks.jsonl

Query    → embed → cosine similarity (top-4 chunks)
         → LLM (Ollama /api/chat) → Telegram response
```

**Stack:** aiogram 3 (FSM) · aiohttp · aiosqlite · NumPy · BeautifulSoup4 · pypdf

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) running locally (`ollama serve`)
- Models pulled:
  ```bash
  ollama pull qwen3:4b          # or any chat model
  ollama pull nomic-embed-text  # embedding model
  ```

## Quick Start

```bash
git clone https://github.com/yourusername/rag-aiogram-bot
cd rag-aiogram-bot

pip install -r requirements.txt

cp .env.example .env
# Fill in TELEGRAM_TOKEN and adjust model names if needed

python run.py
```

## Configuration

All settings are in `.env` (see [.env.example](.env.example)):

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_TOKEN` | — | **Required.** Bot token from @BotFather |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_CHAT_MODEL` | `qwen3:4b` | Chat model name |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `OLLAMA_TIMEOUT_SEC` | `120` | HTTP timeout for Ollama requests |
| `REQUIRED_CHANNEL` | — | Optional channel username for subscription gate |
| `ADMINS` | — | Comma-separated Telegram user IDs with admin access |
| `WORK_TIME_START` / `WORK_TIME_END` | `08:00` / `23:00` | Operating hours (admins bypass) |
| `DATA_DIR` | `data/` | Root directory for indexes, DB, and temp files |

## Project Structure

```
├── run.py                  # Entry point
├── create_bot.py           # Bot/dispatcher/middleware wiring
├── config.py               # Settings dataclass
├── handlers/               # FSM handlers (start, menu, article, qa, prompt, cancel)
├── services/
│   ├── rag_engine.py       # RAG orchestration (index, search, answer, summarize)
│   ├── vector_store.py     # NumPy vector DB
│   └── loaders.py          # Document loaders (URL / PDF / TXT)
├── db_handler/             # Async SQLite (user settings)
├── middlewares/            # Subscription & work-time checks
├── keyboards/              # Telegram button layouts
├── utils/                  # Text chunking, URL detection, message splitting
├── check_ollama.py         # Ollama connectivity health check
└── data/                   # Runtime: indexes/, user_data.db, tmp/
```

## License

MIT
