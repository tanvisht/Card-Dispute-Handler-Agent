"""Small text helpers shared by classifiers."""
from __future__ import annotations

import re

# "$3,450.00", "$ 1200", "USD 950", "1,200 dollars", "1200.50 usd"
_MONEY = re.compile(
    r"(?:\$|\busd\s?)\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?"
    r"|\b(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?\s?(?:dollars?|usd)\b",
    re.IGNORECASE,
)


def extract_amounts(text: str) -> list[float]:
    """Return every currency amount mentioned in the text, in order.

    CFPB redacts many amounts as "{$XXXX}" / "XXXX"; those are skipped by design.
    """
    out = []
    for m in _MONEY.finditer(text):
        whole = m.group(1) or m.group(3)
        cents = m.group(2) or m.group(4) or "0"
        out.append(float(f"{whole.replace(',', '')}.{cents}"))
    return out


def max_amount(text: str) -> float:
    amounts = extract_amounts(text)
    return max(amounts) if amounts else 0.0
