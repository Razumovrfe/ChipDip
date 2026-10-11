from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.fsm import SearchStates
from bot.formatters import render_product_html, render_search_page_html
from bot.keyboards import PER_PAGE, MAX_PAGES, search_pagination
from bot.parser.service import parser_service

router = Router(name="search")


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /search <запрос>\nПример: /search stm32")
        return
    await do_search(message, state, args[1].strip())


async def do_search(message: Message, state: FSMContext, query: str) -> None:
    wait = await message.answer("🔍 Ищу…")
    try:
        items = await parser_service.search(query)
    except Exception as exc:
        logger.warning("/search '{}' failed: {}", query, exc)
        await wait.edit_text("Не удалось выполнить поиск. Попробуйте позже.")
        return
    if not items:
        await wait.edit_text(f"По запросу «{query}» ничего не найдено.")
        return
    items = items[: PER_PAGE * MAX_PAGES]
    await state.set_state(SearchStates.results)
    await state.update_data(items=[_item_to_dict(i) for i in items], query=query)
    total_pages = (len(items) + PER_PAGE - 1) // PER_PAGE
    await wait.edit_text(
        render_search_page_html(items, 0, PER_PAGE),
        parse_mode=ParseMode.HTML,
        reply_markup=search_pagination(0, total_pages),
    )


@router.callback_query(F.data == "s:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(SearchStates.results, F.data.startswith("s:"))
async def cb_search_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    items = data.get("items", [])
    if not items:
        await callback.answer("Сессия истекла, выполните /search заново.", show_alert=True)
        return
    total_pages = (len(items) + PER_PAGE - 1) // PER_PAGE
    page = max(0, min(page, total_pages - 1))
    await callback.message.edit_text(
        render_search_page_html(_restore_items(items), page, PER_PAGE),
        parse_mode=ParseMode.HTML,
        reply_markup=search_pagination(page, total_pages),
    )
    await callback.answer()


@router.callback_query(SearchStates.results, F.data.startswith("si:"))
async def cb_search_item(callback: CallbackQuery, state: FSMContext) -> None:
    idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    items = data.get("items", [])
    if idx < 0 or idx >= len(items):
        await callback.answer("Элемент недоступен.", show_alert=True)
        return
    url = items[idx]["url"]
    await callback.answer("Загружаю карточку…")
    try:
        product = await parser_service.product(url)
    except Exception as exc:
        logger.warning("search item info failed: {}", exc)
        await callback.message.answer("Не удалось получить карточку.")
        return
    if product is None:
        await callback.message.answer("Товар не найден.")
        return
    await callback.message.answer(render_product_html(product), parse_mode=ParseMode.HTML)


def _item_to_dict(i) -> dict:
    return {
        "title": i.title,
        "url": i.url,
        "price": i.price,
        "available": i.available,
        "availability": i.availability,
        "article": i.article,
    }


def _restore_items(items: list[dict]):
    from bot.parser.models import SearchItem

    return [
        SearchItem(
            article=it["article"],
            title=it["title"],
            url=it["url"],
            price=it["price"],
            available=it["available"],
            availability=it["availability"],
        )
        for it in items
    ]
