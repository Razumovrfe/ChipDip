from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from bot.parser.models import Product
from bot.parser.util import to_float as _to_float


def parse_product(html: str, url: str, base_url: str = "https://www.chipdip.by") -> Product | None:
    soup = BeautifulSoup(html, "lxml")

    h1 = soup.select_one("h1[itemprop='name']") or soup.find("h1")
    if not h1:
        return None
    title = h1.get_text(" ", strip=True)

    sku_el = soup.select_one("span[itemprop='sku']")
    sku = sku_el.get_text(strip=True) if sku_el else ""

    model_el = soup.select_one("span[itemprop='model']")
    article = model_el.get_text(strip=True) if model_el else sku

    brand_el = soup.select_one("span[itemprop='brand']")
    brand = brand_el.get_text(strip=True) if brand_el else None

    price = None
    price_meta = soup.select_one("meta[itemprop='price']")
    if price_meta and price_meta.get("content"):
        price = _to_float(price_meta["content"])
    if price is None:
        price_span = soup.select_one("span.ordering__value[id^='price_']") or soup.select_one(
            "span[id^='price_']"
        )
        price = _to_float(price_span.get_text(strip=True)) if price_span else None

    low_price = None
    low_meta = soup.select_one("meta[itemprop='lowPrice']")
    if low_meta and low_meta.get("content"):
        low_price = _to_float(low_meta["content"])

    currency = "BYN"
    curr_meta = soup.select_one("meta[itemprop='priceCurrency']")
    if curr_meta and curr_meta.get("content"):
        currency = curr_meta["content"]

    avail_link = soup.select_one("link[itemprop='availability']")
    in_stock = bool(avail_link and "InStock" in avail_link.get("href", ""))

    avail_rows = soup.select(".product__extrainfo-row span.item__avail")
    if not avail_rows:
        avail_rows = soup.select("#ordering span.item__avail")
    availability = "; ".join(
        r.get_text(" ", strip=True).replace("\xa0", " ") for r in avail_rows if r.get_text(strip=True)
    )
    if not availability:
        availability = "В наличии" if in_stock else "Нет в наличии"

    desc_el = soup.select_one("div[itemprop='description']")
    description = desc_el.get_text(" ", strip=True) if desc_el else ""

    characteristics: dict[str, str] = {}
    for table in soup.select("table#productparams, div[itemprop='description'] table"):
        for tr in table.select("tr"):
            cells = tr.find_all("td", recursive=False)
            if len(cells) >= 2:
                key = cells[0].get_text(" ", strip=True)
                val = cells[1].get_text(" ", strip=True)
                if key and val and key not in characteristics:
                    characteristics[key] = val

    return Product(
        article=article,
        sku=sku,
        title=title,
        url=urljoin(base_url, url) if not url.startswith("http") else url,
        brand=brand,
        price=price,
        low_price=low_price,
        currency=currency,
        in_stock=in_stock,
        availability=availability,
        description=description,
        characteristics=characteristics,
    )
