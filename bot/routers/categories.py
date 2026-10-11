from __future__ import annotations

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.fsm import CategoryStates
from bot.formatters import render_search_page_html
from bot.keyboards import (
    PER_PAGE,
    MAX_PAGES,
    categories_keyboard,
    category_products_keyboard,
)
from bot.parser.service import parser_service

router = Router(name="categories")


@router.message(Command("categories"))
async def cmd_categories(message: Message, state: FSMContext) -> None:
    wait = await message.answer("Загружаю каталог…")
    try:
        tree = await parser_service.category_tree()
    except Exception as exc:
        logger.warning("category_tree failed: {}", exc)
        await wait.edit_text("Не удалось загрузить каталог. Попробуйте позже.")
        return
    if not tree:
        await wait.edit_text("Каталог недоступен.")
        return
    await state.set_state(CategoryStates.browsing)
    await state.update_data(stack=[], items=_nodes_to_dicts(tree), title="Каталог", products=None)
    await wait.edit_text(
        "<b>Каталог</b>\nВыберите категорию:",
        parse_mode=ParseMode.HTML,
        reply_markup=categories_keyboard(tree, back=False),
    )


@router.callback_query(CategoryStates.browsing, F.data.startswith("c:"))
async def cb_category(callback: CallbackQuery, state: FSMContext) -> None:
    data = callback.data
    if data == "c:back":
        await _go_back(callback, state)
        return
    if data == "c:noop":
        await callback.answer()
        return
    idx = int(data.split(":")[1])
    state_data = await state.get_data()
    items = state_data.get("items", [])
    if idx < 0 or idx >= len(items):
        await callback.answer("Элемент недоступен.", show_alert=True)
        return
    item = items[idx]
    await callback.answer()
    if item.get("children"):
        await _show_children(callback, state, item, items)
    else:
        await _open_leaf(callback, state, item, items)


async def _show_children(callback: CallbackQuery, state: FSMContext, item: dict, parent_items: list) -> None:
    children = item["children"]
    stack = (await state.get_data()).get("stack", [])
    stack.append({"items": parent_items, "title": (await state.get_data()).get("title", "")})
    await state.update_data(stack=stack, items=children, title=item["name"], products=None)
    await callback.message.edit_text(
        f"<b>{item['name']}</b>\nВыберите подкатегорию:",
        parse_mode=ParseMode.HTML,
        reply_markup=categories_keyboard(_dicts_to_nodes(children), back=True),
    )


async def _open_leaf(callback: CallbackQuery, state: FSMContext, item: dict, parent_items: list) -> None:
    from bot.parser.pages.category import has_products, parse_subcategories

    url = item["url"]
    name = item["name"]
    try:
        html = await parser_service._cached(url)  # noqa: SLF001
    except Exception as exc:
        logger.warning("category fetch failed for {}: {}", url, exc)
        await callback.message.answer("Не удалось загрузить категорию. Попробуйте позже.")
        return

    subs = parse_subcategories(html, parser_service._base)  # noqa: SLF001
    if subs:
        stack = (await state.get_data()).get("stack", [])
        stack.append({"items": parent_items, "title": (await state.get_data()).get("title", "")})
        children = [_cat_to_dict(c) for c in subs]
        await state.update_data(stack=stack, items=children, title=name, products=None)
        await callback.message.edit_text(
            f"<b>{name}</b>\nВыберите подкатегорию:",
            parse_mode=ParseMode.HTML,
            reply_markup=categories_keyboard(_dicts_to_nodes(children), back=True),
        )
        return

    items_list = await parser_service.category_products(url) if has_products(html) else []
    items_list = items_list[: PER_PAGE * MAX_PAGES]
    if not items_list:
        await callback.message.answer(f"В категории «{name}» нет товаров.")
        return
    stack = (await state.get_data()).get("stack", [])
    stack.append({"items": parent_items, "title": (await state.get_data()).get("title", "")})
    await state.update_data(
        stack=stack,
        items=[_search_item_to_dict(i) for i in items_list],
        title=name,
        products=[_search_item_to_dict(i) for i in items_list],
    )
    total_pages = (len(items_list) + PER_PAGE - 1) // PER_PAGE
    await callback.message.edit_text(
        render_search_page_html(items_list, 0, PER_PAGE),
        parse_mode=ParseMode.HTML,
        reply_markup=category_products_keyboard(0, total_pages),
    )


@router.callback_query(CategoryStates.browsing, F.data == "cp:noop")
async def cb_cat_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(CategoryStates.browsing, F.data.startswith("cp:"))
async def cb_cat_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    products = data.get("products") or []
    if not products:
        await callback.answer("Сессия истекла, откройте /categories заново.", show_alert=True)
        return
    from bot.parser.models import SearchItem

    items = [
        SearchItem(
            article=p["article"],
            title=p["title"],
            url=p["url"],
            price=p["price"],
            available=p["available"],
            availability=p["availability"],
        )
        for p in products
    ]
    total_pages = (len(items) + PER_PAGE - 1) // PER_PAGE
    page = max(0, min(page, total_pages - 1))
    await callback.message.edit_text(
        render_search_page_html(items, page, PER_PAGE),
        parse_mode=ParseMode.HTML,
        reply_markup=category_products_keyboard(page, total_pages),
    )
    await callback.answer()


async def _go_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    stack = data.get("stack", [])
    if not stack:
        await callback.answer()
        return
    prev = stack.pop()
    await state.update_data(stack=stack, items=prev["items"], title=prev["title"], products=None)
    await callback.message.edit_text(
        f"<b>{prev['title']}</b>\nВыберите категорию:",
        parse_mode=ParseMode.HTML,
        reply_markup=categories_keyboard(_dicts_to_nodes(prev["items"]), back=bool(stack)),
    )
    await callback.answer()


def _nodes_to_dicts(nodes) -> list[dict]:
    return [
        {
            "name": n.name,
            "url": n.url,
            "count": n.count,
            "children": _nodes_to_dicts(n.children) if n.children else None,
        }
        for n in nodes
    ]


def _cat_to_dict(c) -> dict:
    return {"name": c.name, "url": c.url, "count": c.count, "children": None}


def _search_item_to_dict(i) -> dict:
    return {
        "article": i.article,
        "title": i.title,
        "url": i.url,
        "price": i.price,
        "available": i.available,
        "availability": i.availability,
    }


def _dicts_to_nodes(dicts: list[dict]):
    from bot.parser.models import CategoryNode

    return [
        CategoryNode(
            name=d["name"],
            url=d["url"],
            count=d.get("count"),
            children=_dicts_to_nodes(d["children"]) if d.get("children") else [],
        )
        for d in dicts
    ]
