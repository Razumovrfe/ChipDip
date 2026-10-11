from __future__ import annotations

from pathlib import Path

import pytest

from bot.parser.pages.category import (
    has_products,
    parse_catalog_tree,
    parse_subcategories,
)
from bot.parser.pages.product import parse_product
from bot.parser.pages.search import parse_search

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_product():
    html = _load("product.html")
    product = parse_product(html, "https://www.chipdip.by/product/stm32f103c8t6")
    assert product is not None
    assert "STM32F103C8T6" in product.title
    assert product.sku == "9000099899"
    assert product.article == "STM32F103C8T6"
    assert product.brand == "STMicroelectronics"
    assert product.price == 6
    assert product.currency == "BYN"
    assert product.in_stock is True
    assert "27" in product.availability
    assert product.characteristics
    assert any("Серия" in k or "Ядро" in k for k in product.characteristics)


def test_parse_search():
    html = _load("search.html")
    items = parse_search(html)
    assert len(items) >= 5
    first = items[0]
    assert first.title
    assert first.url.startswith("https://www.chipdip.by/product/")
    assert first.article  # row id present
    # at least one priced item
    assert any(it.price is not None for it in items)


def test_parse_catalog_tree():
    html = _load("category.html")
    tree = parse_catalog_tree(html)
    assert tree
    node = tree[0]
    assert node.name
    assert node.url.startswith("https://www.chipdip.by/catalog/")
    assert node.children
    assert node.children[0].url.startswith("https://www.chipdip.by/catalog/")


def test_parse_subcategories():
    html = _load("category_items.html")
    subs = parse_subcategories(html)
    assert subs
    assert all(
        s.url.startswith(("https://www.chipdip.by/catalog/", "https://www.chipdip.by/catalog-show/"))
        for s in subs
    )
    assert any(s.count is not None for s in subs)


def test_has_products_index_false():
    assert has_products(_load("category_items.html")) is False


def test_has_products_search_true():
    assert has_products(_load("search.html")) is True


def test_parse_subcategories_leaf():
    subs = parse_subcategories(_load("leaf.html"))
    assert len(subs) == 2
    names = {s.name for s in subs}
    assert any("Клеи" in n for n in names)
    assert all(s.url.startswith("https://www.chipdip.by/catalog-show/") for s in subs)
    assert all(s.count is not None for s in subs)


def test_parse_catalog_items():
    from bot.parser.pages.search import parse_catalog_items

    items = parse_catalog_items(_load("catalog_show.html"))
    assert len(items) >= 20
    first = items[0]
    assert first.title
    assert first.url.startswith("https://www.chipdip.by/product/")
    assert first.article
    assert first.price is not None
    assert first.price > 0


def test_has_products_catalog_show_true():
    assert has_products(_load("catalog_show.html")) is True
