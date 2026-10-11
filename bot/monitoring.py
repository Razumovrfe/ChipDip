from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ParseMode
from loguru import logger

from bot.db.repo import repo
from bot.formatters import render_product_html
from bot.parser.service import parser_service

FAIL_THRESHOLD = 5


async def run_monitoring(bot: Bot) -> None:
    logger.info("Monitoring tick: start")
    try:
        tracks = await repo.active_tracks()
    except Exception as exc:
        logger.error("Failed to load active tracks: {}", exc)
        return
    logger.info("Monitoring: {} active tracks", len(tracks))
    for t in tracks:
        await _check_one(bot, t)
    await repo.cache_cleanup()
    logger.info("Monitoring tick: done")


async def _check_one(bot: Bot, track: dict) -> None:
    track_id = track["id"]
    tg_id = track["tg_id"]
    url = track["url"]
    threshold = track["threshold"]
    try:
        product = await parser_service.product(url)
    except Exception as exc:
        logger.warning("track {} fetch error: {}", track_id, exc)
        fails = await repo.increment_track_fail(track_id)
        if fails >= FAIL_THRESHOLD:
            await repo.deactivate_track(track_id)
            await _notify(bot, tg_id, f"⚠️ Трек деактивирован после {fails} ошибок подряд:\n{url}")
        return

    if product is None:
        await repo.deactivate_track(track_id)
        await _notify(
            bot, tg_id, f"❌ Товар больше недоступен, трек деактивирован:\n{url}"
        )
        return

    price = product.price
    await repo.update_track_price(track_id, price, reset_fail=True)

    if price is not None and price < threshold:
        if not track.get("notified_below") and not _was_notified(track):
            await repo.update_track_price(track_id, price, set_notified=True)
            await _notify(
                bot,
                tg_id,
                "📉 Цена ниже порога!\n"
                f"{render_product_html(product)}\n\n"
                f"Порог: {threshold} BYN, текущая: {price} BYN",
            )
    else:
        if _was_notified(track):
            await repo.reset_notified(track_id)


def _was_notified(track: dict) -> bool:
    return bool(track.get("notified_below"))


async def _notify(bot: Bot, tg_id: int, text: str) -> None:
    try:
        await bot.send_message(tg_id, text, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.warning("notify to {} failed: {}", tg_id, exc)
