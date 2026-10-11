from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent, Update
from loguru import logger

from bot.config import get_settings


def build_bot() -> Bot:
    settings = get_settings()
    return Bot(token=settings.telegram_bot_token)


def build_dispatcher(bot: Bot) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    from bot.routers import categories, info, mytracks, search, start, track

    dp.include_router(start.router)
    dp.include_router(info.router)
    dp.include_router(search.router)
    dp.include_router(track.router)
    dp.include_router(mytracks.router)
    dp.include_router(categories.router)

    @dp.errors()
    async def on_error(event: ErrorEvent) -> None:
        update = event.update
        exc = event.exception
        logger.exception("Unhandled exception for update {}: {}", getattr(update, "update_id", "?"), exc)
        chat_id = _extract_chat_id(update)
        if chat_id is not None:
            try:
                await bot.send_message(chat_id, "Произошла ошибка. Попробуйте позже.")
            except Exception:
                pass

    return dp


def _extract_chat_id(update: Update) -> int | None:
    try:
        return update.get_event().from_user.id  # type: ignore[union-attr]
    except Exception:
        return None
