from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import Settings


def main_menu_kb(settings: Settings, has_article: bool) -> ReplyKeyboardMarkup:
    """Главное меню.

    Если статья уже загружена — показываем кнопки вопросов/резюме.
    """
    rows = []

    if has_article:
        rows.append([KeyboardButton(text=settings.BTN_ASK)])
        rows.append([KeyboardButton(text=settings.BTN_SUMMARY)])

    rows.append([KeyboardButton(text=settings.BTN_UPLOAD)])
    rows.append([KeyboardButton(text=settings.BTN_PROMPT)])
    rows.append([KeyboardButton(text=settings.BTN_RESET)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb(settings: Settings) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=settings.BTN_CANCEL)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def prompt_menu_kb(settings: Settings) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=settings.BTN_PROMPT_DEFAULT)],
            [KeyboardButton(text=settings.BTN_PROMPT_CUSTOM)],
            [KeyboardButton(text=settings.BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
