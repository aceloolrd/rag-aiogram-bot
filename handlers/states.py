from aiogram.fsm.state import StatesGroup, State


class MainMenu(StatesGroup):
    waiting_choice = State()


class ArticleFlow(StatesGroup):
    waiting_source = State()


class QAFlow(StatesGroup):
    waiting_question = State()


class PromptFlow(StatesGroup):
    waiting_choice = State()
    waiting_custom_prompt = State()
