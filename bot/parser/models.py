from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SearchItem:
    article: str
    title: str
    url: str
    price: float | None
    available: bool
    availability: str


@dataclass(slots=True)
class Product:
    article: str
    sku: str
    title: str
    url: str
    brand: str | None
    price: float | None
    low_price: float | None
    currency: str
    in_stock: bool
    availability: str
    description: str
    characteristics: dict[str, str]


@dataclass(slots=True)
class Category:
    name: str
    url: str
    count: int | None


@dataclass(slots=True)
class CategoryNode:
    name: str
    url: str
    count: int | None
    children: list["CategoryNode"]
