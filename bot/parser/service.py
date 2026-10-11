from __future__ import annotations

from urllib.parse import urljoin

import httpx
from loguru import logger

from bot.config import get_settings
from bot.parser.cache import cache
from bot.parser.http_client import HttpClient, _is_challenge
from bot.parser.models import Category, CategoryNode, Product, SearchItem
from bot.parser.pages.category import (
    has_products,
    parse_catalog_tree,
    parse_subcategories,
)
from bot.parser.pages.product import parse_product
from bot.parser.pages.search import parse_catalog_items, parse_search, search_url

# A page shorter than this is definitely not a real catalog/product page.
_MIN_REAL_HTML = 5000


class ParserService:
    def __init__(self) -> None:
        self.http = HttpClient()
        self._base = get_settings().chipdip_url.rstrip("/")

    async def start(self) -> None:
        await self.http.start()

    async def close(self) -> None:
        await self.http.close()
        from bot.parser.selenium_worker import shutdown

        await shutdown()

    def _abs(self, url: str) -> str:
        return urljoin(self._base + "/", url)

    async def _httpx_probe(self, url: str) -> tuple[str | None, bool]:
        """Fast httpx attempt without rate-limit. Returns (html, not_found).
        - html is set only if it is real content (not a challenge/block page).
        - not_found is True on a 404 (page genuinely absent — caller should stop
          paginating, and Selenium won't help).
        Used as an optimization: if the site ever stops bot-blocking, httpx
        takes over automatically.
        """
        if not get_settings().use_selenium_fallback:
            # Selenium disabled -> httpx is the only path, use full get().
            try:
                return await self.http.get_text(url), False
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    return "", True
                raise
        try:
            resp = await self.http.client.get(url, headers=self.http._headers(), timeout=6.0)
            if resp.status_code == 404:
                return "", True
            if resp.status_code == 200 and not _is_challenge(resp.text) and len(resp.text) >= _MIN_REAL_HTML:
                return resp.text, False
        except Exception as exc:
            logger.debug("httpx probe failed for {}: {}", url, exc)
        return None, False

    async def _fetch(self, url: str) -> str:
        html, not_found = await self._httpx_probe(url)
        if html:
            return html
        if not_found:
            # Genuine 404 — Selenium can't conjure a missing page. Return empty.
            return ""
        return await self._selenium(url)

    async def _selenium(self, url: str) -> str:
        from bot.parser.selenium_worker import fetch

        return await fetch(url)

    async def _cached(self, url: str, *, force: bool = False) -> str:
        if not force:
            cached = await cache.get(url)
            if cached and not _is_challenge(cached) and len(cached) >= _MIN_REAL_HTML:
                return cached
        html = await self._fetch(url)
        if html and not _is_challenge(html) and len(html) >= _MIN_REAL_HTML:
            await cache.set(url, html)
        return html

    async def search(self, query: str) -> list[SearchItem]:
        url = search_url(query, self._base)
        html = await self._cached(url)
        return parse_search(html, self._base) if html else []

    async def product(self, url: str) -> Product | None:
        url = self._abs(url)
        html = await self._cached(url)
        return parse_product(html, url, self._base) if html else None

    async def category_tree(self) -> list[CategoryNode]:
        url = f"{self._base}/catalog"
        html = await self._cached(url)
        return parse_catalog_tree(html, self._base) if html else []

    async def subcategories(self, url: str) -> list[Category]:
        url = self._abs(url)
        html = await self._cached(url)
        return parse_subcategories(html, self._base) if html else []

    async def category_products(self, url: str) -> list[SearchItem]:
        url = self._abs(url)
        max_pages = get_settings().max_search_pages
        seen: set[str] = set()
        merged: list[SearchItem] = []
        for page in range(1, max_pages + 1):
            page_url = url if page == 1 else f"{url}{'&' if '?' in url else '?'}page={page}"
            try:
                html = await self._cached(page_url)
            except Exception as exc:
                logger.warning("category_products fetch failed for {}: {}", page_url, exc)
                break
            if not html or not has_products(html):
                break
            items = parse_catalog_items(html, self._base) or parse_search(html, self._base)
            if not items:
                break
            for it in items:
                if it.url not in seen:
                    seen.add(it.url)
                    merged.append(it)
            if len(merged) >= 50:
                break
        return merged[:50]

    async def fetch_price(self, url: str) -> Product | None:
        return await self.product(url)


parser_service = ParserService()
