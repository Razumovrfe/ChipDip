from __future__ import annotations

from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from bot.formatters import render_product_html
from bot.parser.service import parser_service

router = Router(name="info")


@router.message(Command("info"))
async def cmd_info(message: Message) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            "Использование: /info <url>\n"
            "Пример: /info https://www.chipdip.by/product/stm32f103c8t6"
        )
        return
    url = args[1].strip()
    wait = await message.answer("Загружаю карточку…")
    try:
        product = await parser_service.product(url)
    except Exception as exc:
        logger.warning("/info failed for {}: {}", url, exc)
        await wait.edit_text("Не удалось получить карточку. Проверьте URL.")
        return
    if product is None:
        await wait.edit_text("Товар не найден. Проверьте URL.")
        return
    try:
        await wait.edit_text(render_product_html(product), parse_mode=ParseMode.HTML)
    except Exception:
        await message.answer(render_product_html(product), parse_mode=ParseMode.HTML)
