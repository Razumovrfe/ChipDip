from __future__ import annotations

import sys

from loguru import logger

from bot.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        diagnose=False,
        backtrace=False,
        enqueue=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
    )
    logger.add(
        settings.log_path / "bot.log",
        level="DEBUG",
        rotation="5 MB",
        retention=10,
        encoding="utf-8",
        diagnose=False,
        backtrace=True,
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
    )
