from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from bot.bot import build_bot, build_dispatcher
from bot.config import get_settings
from bot.db.connection import init_db
from bot.logging_config import setup_logging
from bot.monitoring import run_monitoring
from bot.parser.service import parser_service


async def main() -> None:
    setup_logging()
    settings = get_settings()
    logger.info("Starting ChipDip bot")

    await init_db()
    await parser_service.start()

    bot = build_bot()
    dp = build_dispatcher(bot)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_monitoring,
        IntervalTrigger(minutes=settings.check_interval_minutes),
        args=[bot],
        id="monitoring",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started, interval {} min", settings.check_interval_minutes)

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await parser_service.close()
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
