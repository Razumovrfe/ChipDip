from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any

import httpx
from loguru import logger

from bot.config import get_settings

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_CHALLENGE_RE = re.compile(r"<title>Verification</title>")
_HG_SECURITY_RE = re.compile(r'hg-security=([^";]+)')


def _is_challenge(text: str) -> bool:
    return bool(text) and len(text) < 4000 and bool(_CHALLENGE_RE.search(text))


def _extract_hg_security(text: str) -> str | None:
    m = _HG_SECURITY_RE.search(text or "")
    return m.group(1) if m else None


class RateLimiter:
    async def acquire(self) -> None:
        raise NotImplementedError


class TimedRateLimiter(RateLimiter):
    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()


class HttpClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._timeout = settings.parser_timeout_seconds
        self._retries = settings.parser_max_retries
        self._rate = TimedRateLimiter(settings.request_delay_seconds)
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"},
            )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": random.choice(USER_AGENTS)}

    async def get(self, url: str) -> httpx.Response:
        await self.start()
        assert self._client is not None
        backoff = 1.0
        last_exc: Exception | None = None
        for attempt in range(1, self._retries + 1):
            await self._rate.acquire()
            try:
                logger.debug("GET {} (attempt {})", url, attempt)
                resp = await self._client.get(url, headers=self._headers())
                # JS anti-bot challenge: parse hg-security cookie and retry once.
                if _is_challenge(resp.text):
                    sec = _extract_hg_security(resp.text)
                    if sec:
                        logger.debug("Challenge detected for {}, retrying with hg-security cookie", url)
                        self._client.cookies.set(
                            name="hg-security", value=sec, domain="www.chipdip.by"
                        )
                        await self._rate.acquire()
                        resp = await self._client.get(url, headers=self._headers())
                if resp.status_code in (403, 429, 503) or _is_challenge(resp.text):
                    # Hard block — don't retry httpx, let the service fall back to Selenium.
                    raise httpx.HTTPStatusError(
                        f"blocked {resp.status_code}", request=resp.request, response=resp
                    )
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning("GET {} failed (attempt {}): {}", url, attempt, exc)
                if attempt < self._retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
        assert last_exc is not None
        raise last_exc

    async def get_text(self, url: str) -> str:
        resp = await self.get(url)
        return resp.text

    @property
    def client(self) -> httpx.AsyncClient:
        assert self._client is not None, "HttpClient not started"
        return self._client


_rate_limiter: TimedRateLimiter | None = None


def get_rate_limiter() -> TimedRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TimedRateLimiter(get_settings().request_delay_seconds)
    return _rate_limiter


async def acquire_global() -> Any:
    await get_rate_limiter().acquire()
    return None
