from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

PER_PAGE = 10
MAX_PAGES = 5


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔍 Поиск")
    kb.button(text="📂 Категории")
    kb.button(text="📋 Мои треки")
    kb.button(text="ℹ️ Помощь")
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


def pagination_keyboard(page: int, total_pages: int, prefix: str = "s:") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if page > 0:
        kb.button(text="◀️ Назад", callback_data=f"{prefix}{page - 1}")
    kb.button(text=f"{page + 1}/{total_pages}", callback_data=f"{prefix}noop")
    if page < total_pages - 1:
        kb.button(text="Вперёд ▶️", callback_data=f"{prefix}{page + 1}")
    kb.adjust(3, 1)
    return kb.as_markup()


def search_pagination(page: int, total_pages: int) -> InlineKeyboardMarkup:
    return pagination_keyboard(page, total_pages, prefix="s:")


def category_products_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    return pagination_keyboard(page, total_pages, prefix="cp:")


def tracks_keyboard(tracks: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in tracks:
        title = (t.get("title") or t.get("url") or f"#{t['id']}")
        if len(title) > 60:
            title = title[:57] + "…"
        kb.button(text=f"🗑 {title}", callback_data=f"u:{t['id']}")
    kb.adjust(1)
    return kb.as_markup()


def categories_keyboard(nodes: list, back: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, node in enumerate(nodes):
        name = node.name
        if getattr(node, "count", None) is not None:
            name = f"{name} ({node.count})"
        if len(name) > 50:
            name = name[:47] + "…"
        kb.button(text=name, callback_data=f"c:{i}")
    if back:
        kb.button(text="◀️ Назад", callback_data="c:back")
    kb.adjust(1)
    return kb.as_markup()
