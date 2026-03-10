from __future__ import annotations

import io
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup
from pypdf import PdfReader

from utils.my_utils import normalize_whitespace


@dataclass(frozen=True)
class LoadedDocument:
    text: str
    source_title: str


async def load_from_url(url: str, timeout_sec: int = 25) -> LoadedDocument:
    """Скачиваем страницу и извлекаем текст.

    Мы не тянем “умные” парсеры вроде readability, чтобы проект работал из коробки.
    Зато стараемся:
    - сначала искать <article>
    - иначе брать <body>
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RAGArticleBot/1.0; +https://telegram.org)"
    }
    timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            html = await resp.text(errors="ignore")

    soup = BeautifulSoup(html, "html.parser")

    # выкидываем мусор
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    article = soup.find("article")
    if article:
        text = article.get_text("\n")
    else:
        body = soup.body or soup
        text = body.get_text("\n")

    text = normalize_whitespace(text)

    if len(text) < 200:
        raise ValueError("Не получилось извлечь содержательный текст из страницы (слишком мало текста).")

    source_title = title or url
    return LoadedDocument(text=text, source_title=source_title)


def load_from_pdf_bytes(data: bytes, fallback_title: str = "PDF") -> LoadedDocument:
    """Читаем PDF из bytes. Синхронно, но в реальности это не страшно для небольших файлов."""
    reader = PdfReader(io.BytesIO(data))
    pages_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages_text.append(page_text)

    text = normalize_whitespace("\n\n".join(pages_text))
    if len(text) < 50:
        raise ValueError("PDF выглядит пустым или текст не извлекается (возможно, это скан).")

    return LoadedDocument(text=text, source_title=fallback_title)


def load_from_txt_bytes(data: bytes, fallback_title: str = "TXT") -> LoadedDocument:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1251", errors="ignore")

    text = normalize_whitespace(text)
    if len(text) < 20:
        raise ValueError("TXT файл слишком короткий — нечего индексировать.")

    return LoadedDocument(text=text, source_title=fallback_title)
