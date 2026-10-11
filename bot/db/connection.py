from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

from bot.config import get_settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db() -> None:
    db_path = get_settings().db_path
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        await db.executescript(schema)
        await db.commit()


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    db_path = get_settings().db_path
    db = await aiosqlite.connect(db_path)
    try:
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()
