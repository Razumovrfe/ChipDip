from __future__ import annotations

import re

_THOUSANDS = re.compile(r"[\s\u00a0\u202f\u2009\u2007]+")


def to_float(text: str | None) -> float | None:
    if text is None:
        return None
    cleaned = _THOUSANDS.sub("", text).strip()
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None
