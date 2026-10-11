from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import SearchStates
from bot.keyboards import main_menu_keyboard

router = Router(name="start")

HELP_TEXT = (
    "ЧИП и ДИП — бот для поиска и мониторинга цен на chipdip.by\n\n"
    "Команды:\n"
    "/search <запрос> — поиск товаров\n"
    "/info <url> — карточка товара\n"
    "/track <url> <порог> — следить за ценой (уведомление при снижении ниже порога)\n"
    "/mytracks — список отслеживаемых товаров\n"
    "/categories — каталог категорий\n"
    "/help — эта справка\n\n"
    "Лимит: 50 треков на пользователя."
)

MENU = main_menu_keyboard()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=MENU)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=MENU)


@router.message(F.text == "🔍 Поиск")
async def menu_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_query)
    await message.answer("Введите поисковый запрос:", reply_markup=MENU)


@router.message(F.text == "📂 Категории")
async def menu_categories(message: Message, state: FSMContext) -> None:
    from bot.routers.categories import cmd_categories

    await cmd_categories(message, state)


@router.message(F.text == "📋 Мои треки")
async def menu_mytracks(message: Message) -> None:
    from bot.routers.mytracks import cmd_mytracks

    await cmd_mytracks(message)


@router.message(F.text == "ℹ️ Помощь")
async def menu_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=MENU)


@router.message(SearchStates.waiting_query, F.text)
async def menu_search_query(message: Message, state: FSMContext) -> None:
    from bot.routers.search import do_search

    query = (message.text or "").strip()
    await state.clear()
    await do_search(message, state, query)
