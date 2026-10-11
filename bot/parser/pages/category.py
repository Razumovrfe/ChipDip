from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from bot.parser.models import Category, CategoryNode
from bot.parser.pages.search import parse_search  # noqa: F401  (reuse for leaf listings)


def _count(sub) -> int | None:
    if sub is None:
        return None
    text = sub.get_text(strip=True).replace(" ", "").replace("\xa0", "")
    try:
        return int(text)
    except ValueError:
        return None


def parse_catalog_tree(html: str, base_url: str = "https://www.chipdip.by") -> list[CategoryNode]:
    soup = BeautifulSoup(html, "lxml")
    nodes: list[CategoryNode] = []
    for g1 in soup.select("div.catalog__g1"):
        header = g1.select_one("a.like-header, a.like-header_3")
        if not header:
            continue
        parent_name = header.get_text(" ", strip=True)
        parent_url = urljoin(base_url, header.get("href", ""))
        parent_count = _count(header.find_next_sibling("sub"))
        children: list[CategoryNode] = []
        for a in g1.select("li.catalog__item > a.link"):
            name = a.get_text(" ", strip=True)
            href = urljoin(base_url, a.get("href", ""))
            cnt = _count(a.find_next_sibling("sub"))
            children.append(CategoryNode(name=name, url=href, count=cnt, children=[]))
        nodes.append(CategoryNode(parent_name, parent_url, parent_count, children))
    return nodes


def _is_cat_link(href: str) -> bool:
    return href.startswith("/catalog/") or href.startswith("/catalog-show/")


def parse_subcategories(html: str, base_url: str = "https://www.chipdip.by") -> list[Category]:
    """Subcategories listed on a /catalog index page (g2 rows).

    Matches both /catalog/ and /catalog-show/ links, but only inside the
    .catalog / .catalog__g2_row containers — excludes breadcrumbs, sidebar,
    footer and related-category links.
    """
    soup = BeautifulSoup(html, "lxml")
    out: list[Category] = []
    seen: set[str] = set()
    container = soup.select_one("div.catalog") or soup
    for row in container.select(".catalog__g2_row"):
        link = row.select_one("a.link")
        if not link:
            continue
        href = link.get("href", "")
        if not _is_cat_link(href):
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        name = link.get_text(" ", strip=True)
        if not name:
            continue
        cnt = _count(link.find_next_sibling("sub"))
        out.append(Category(name=name, url=url, count=cnt))
        seen.add(url)
    return out


def has_products(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    return bool(
        soup.select("tr.with-hover[id^='item']")
        or soup.select("#itemlist div.item[id^='item']")
    )
