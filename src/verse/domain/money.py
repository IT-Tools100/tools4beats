"""Денежная арифметика.

Правило SPEC §6.7: фактический доход и потенциальный доход — разные величины,
и суммы в разных валютах не складываются.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

DEFAULT_CURRENCY = "USD"


def to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip().replace(" ", "").replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Не удалось разобрать сумму: {value!r}") from exc


def add_amount(acc: dict[str, Decimal], currency: str | None, amount: object) -> dict[str, Decimal]:
    """Накапливает суммы по валютам. Никогда не смешивает разные валюты."""
    code = (currency or DEFAULT_CURRENCY).upper()
    acc[code] = acc.get(code, Decimal("0")) + to_decimal(amount)
    return acc


def total(acc: Mapping[str, Decimal]) -> Decimal:
    """Сумма только если валюта одна; иначе вызывающая сторона показывает разбивку."""
    values = list(acc.values())
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0"))


def format_amount(value: object, currency: str = DEFAULT_CURRENCY) -> str:
    amount = to_decimal(value)
    quant = amount.quantize(Decimal("0.01"))
    text = f"{quant:,.2f}".replace(",", " ")
    return f"{text} {currency.upper()}"


def format_amounts(acc: Mapping[str, Decimal]) -> str:
    """`1 200.00 USD · 300.00 EUR` — без смешивания валют."""
    if not acc:
        return "—"
    parts = [format_amount(amount, code) for code, amount in sorted(acc.items()) if amount != 0]
    return " · ".join(parts) if parts else "—"
