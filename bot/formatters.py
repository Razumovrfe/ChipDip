from __future__ import annotations

from html import escape

from bot.parser.models import Product, SearchItem


def render_product_html(p: Product) -> str:
    lines = [f"<b>{escape(p.title)}</b>"]
    if p.brand:
        lines.append(f"Бренд: {escape(p.brand)}")
    lines.append(f"Артикул: <code>{escape(p.article)}</code>")
    if p.sku and p.sku != p.article:
        lines.append(f"Номенклатурный №: <code>{escape(p.sku)}</code>")
    price_str = f"{p.price} {p.currency}" if p.price is not None else "—"
    if p.low_price is not None and p.low_price != p.price:
        price_str += f"  (от {p.low_price} {p.currency})"
    lines.append(f"Цена: <b>{escape(price_str)}</b>")
    lines.append(f"Наличие: {escape(p.availability)}")
    if p.description:
        desc = p.description if len(p.description) <= 400 else p.description[:400] + "…"
        lines.append(f"\n<i>{escape(desc)}</i>")
    if p.characteristics:
        lines.append("\n<b>Характеристики:</b>")
        for k, v in list(p.characteristics.items())[:15]:
            lines.append(f"• {escape(k)}: {escape(v)}")
    return "\n".join(lines)


def render_search_page_html(items: list[SearchItem], page: int, per_page: int = 10) -> str:
    start = page * per_page
    chunk = items[start : start + per_page]
    if not chunk:
        return "Ничего не найдено."
    lines = [f"<b>Результаты поиска (стр. {page + 1})</b>\n"]
    for i, it in enumerate(chunk, start=start):
        price = f"{it.price} BYN" if it.price is not None else "—"
        avail = "✅" if it.available else "📦"
        lines.append(f"{i + 1}. {avail} <b>{escape(it.title)}</b>\n   {price} — {escape(it.availability)}\n   {escape(it.url)}")
    return "\n".join(lines)


def render_track_html(track: dict) -> str:
    price = track.get("last_price")
    price_s = f"{price} BYN" if price is not None else "—"
    status = "активен" if track.get("active") else "деактивирован"
    return (
        f"<b>{escape(track.get('title') or track.get('url') or '')}</b>\n"
        f"Порог: <b>{track.get('threshold')} BYN</b> | Текущая: {price_s} | {status}\n"
        f"{escape(track.get('url') or '')}"
    )
