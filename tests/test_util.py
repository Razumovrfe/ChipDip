from __future__ import annotations

import pytest

from bot.parser.util import to_float


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("6", 6.0),
        ("5.60", 5.6),
        ("1\xa0420", 1420.0),
        ("1 050", 1050.0),
        ("1\u202f500", 1500.0),
        ("1 420,50", 1420.5),
        ("850", 850.0),
        ("1,5", 1.5),
        ("", None),
        (None, None),
        ("—", None),
    ],
)
def test_to_float(raw, expected):
    assert to_float(raw) == expected
