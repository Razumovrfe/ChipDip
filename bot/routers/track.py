from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from bot.db.repo import repo
from bot.fsm import TrackStates
from bot.formatters import render_product_html
from bot.parser.service import parser_service

router = Router(name="track")


def _is_valid_url(url: str) -> bool:
    return "chipdip.by/product/" in url


@router.message(Command("track"))
async def cmd_track(message: Message, state: FSMContext) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) >= 2 and args[1].strip():
        parts = args[1].rsplit(maxsplit=1)
        if len(parts) == 2 and _is_valid_url(parts[0]):
            try:
                threshold = float(parts[1].replace(",", "."))
            except ValueError:
                await message.answer("Порог должен быть числом. Пример: /track <url> 5.5")
                return
            await _add_track(message, state, parts[0].strip(), threshold)
            return
    await state.set_state(TrackStates.waiting_url)
    await message.answer("Пришлите ссылку на товар (chipdip.by/product/…).")


@router.message(TrackStates.waiting_url, F.text)
async def on_url(message: Message, state: FSMContext) -> None:
    url = (message.text or "").strip()
    if not _is_valid_url(url):
        await message.answer("Это не ссылка на товар chipdip.by/product/… Попробуйте снова или /cancel.")
        return
    await state.update_data(url=url)
    await state.set_state(TrackStates.waiting_threshold)
    await message.answer("Введите порог цены (BYN). Уведомлю при снижении ниже порога.")


@router.message(TrackStates.waiting_threshold, F.text)
async def on_threshold(message: Message, state: FSMContext) -> None:
    try:
        threshold = float((message.text or "").replace(",", "."))
    except ValueError:
        await message.answer("Порог должен быть числом. Пример: 5.5")
        return
    data = await state.get_data()
    url = data.get("url")
    await state.clear()
    if not url:
        await message.answer("Сессия истекла. Начните заново /track.")
        return
    await _add_track(message, state, url, threshold)


async def _add_track(message: Message, state: FSMContext, url: str, threshold: float) -> None:
    user_id = await repo.get_or_create_user(message.from_user.id, message.from_user.username)
    count = await repo.count_user_tracks(user_id)
    if count >= get_settings_limit():
        await message.answer("Достигнут лимит треков (50). Удалите ненужные через /mytracks.")
        return
    wait = await message.answer("Проверяю товар…")
    try:
        product = await parser_service.product(url)
    except Exception as exc:
        logger.warning("track product fetch failed: {}", exc)
        await wait.edit_text("Не удалось получить товар. Попробуйте позже.")
        return
    if product is None:
        await wait.edit_text("Товар не найден. Проверьте ссылку.")
        return
    ok = await repo.add_track(
        user_id=user_id,
        url=product.url,
        article=product.article,
        title=product.title,
        threshold=threshold,
        last_price=product.price,
    )
    if not ok:
        await wait.edit_text("Этот товар уже отслеживается.")
        return
    await wait.edit_text(
        f"Добавлено в мониторинг:\n{render_product_html(product)}\n\n"
        f"Порог уведомления: {threshold} BYN",
        parse_mode="HTML",
    )


def get_settings_limit() -> int:
    from bot.config import get_settings

    return get_settings().max_tracks_per_user
