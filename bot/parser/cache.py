from __future__ import annotations

import hashlib

from bot.config import get_settings
from bot.db.repo import repo


def _key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class CacheRepo:
    async def get(self, url: str) -> str | None:
        return await repo.cache_get(_key(url))

    async def set(self, url: str, html: str) -> None:
        ttl = get_settings().cache_ttl_seconds
        await repo.cache_set(_key(url), html, ttl)

    async def cleanup(self) -> None:
        await repo.cache_cleanup()


cache = CacheRepo()
