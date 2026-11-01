"""Денежная арифметика: валюты не смешиваются."""

from __future__ import annotations

from decimal import Decimal

from verse.domain.money import add_amount, format_amount, format_amounts, to_decimal


def test_add_amount_keeps_currencies_separate() -> None:
    acc: dict[str, Decimal] = {}
    add_amount(acc, "usd", "100.50")
    add_amount(acc, "USD", "50")
    add_amount(acc, "eur", 20)
    assert acc["USD"] == Decimal("150.50")
    assert acc["EUR"] == Decimal("20")


def test_to_decimal_accepts_comma() -> None:
    assert to_decimal("1 234,56") == Decimal("1234.56")


def test_format_amount() -> None:
    assert format_amount("1234.5", "usd") == "1 234.50 USD"


def test_format_amounts_empty() -> None:
    assert format_amounts({}) == "—"
