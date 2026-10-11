from __future__ import annotations

from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from bot.parser.models import SearchItem
from bot.parser.util import to_float as _to_float


def search_url(query: str, base_url: str = "https://www.chipdip.by") -> str:
    return f"{base_url.rstrip('/')}/search?searchtext={quote_plus(query)}"


def parse_search(html: str, base_url: str = "https://www.chipdip.by") -> list[SearchItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[SearchItem] = []
    for row in soup.select("tr.with-hover[id^='item']"):
        row_id = (row.get("id") or "").replace("item", "")

        link = row.select_one("td.h_name a.link")
        if not link:
            continue
        title = link.get_text(" ", strip=True)
        href = link.get("href", "")
        url = urljoin(base_url, href)

        avail_span = row.select_one("td.h_av span.item__avail")
        availability = avail_span.get_text(" ", strip=True).replace("\xa0", " ") if avail_span else ""
        available = "item__avail_available" in (avail_span.get("class") if avail_span else [])

        price = None
        price_span = row.select_one("td.h_pr span.price-main span[id^='price_']") or row.select_one(
            "td.h_pr span[id^='price_']"
        )
        if price_span:
            price = _to_float(price_span.get_text(strip=True))

        items.append(
            SearchItem(
                article=row_id,
                title=title,
                url=url,
                price=price,
                available=available,
                availability=availability,
            )
        )
    return items


def parse_catalog_items(html: str, base_url: str = "https://www.chipdip.by") -> list[SearchItem]:
    """Parse product grid on /catalog-show pages (div.item layout)."""
    soup = BeautifulSoup(html, "lxml")
    items: list[SearchItem] = []
    for card in soup.select("div.items#itemlist div.item[id^='item'], #itemlist div.item[id^='item']"):
        row_id = (card.get("id") or "").replace("item", "")
        link = card.select_one("div.item__name a.link")
        if not link:
            continue
        title = link.get_text(" ", strip=True)
        url = urljoin(base_url, link.get("href", ""))

        avail_span = card.select_one("div.item__avail-w span.item__avail")
        availability = avail_span.get_text(" ", strip=True).replace("\xa0", " ") if avail_span else ""
        available = avail_span is not None and "item__avail_available" in avail_span.get("class", [])

        price = None
        price_span = card.select_one("div.item__prices span.price__value[id^='price_']") or card.select_one(
            "span.price__value[id^='price_']"
        )
        if price_span:
            price = _to_float(price_span.get_text(strip=True))

        items.append(
            SearchItem(
                article=row_id,
                title=title,
                url=url,
                price=price,
                available=available,
                availability=availability,
            )
        )
    return items
