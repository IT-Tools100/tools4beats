"""Сделки и платежи: фактический доход не равен потенциальному."""

from __future__ import annotations

from decimal import Decimal

from tests.factories import contact_in
from verse.domain.dto import DealIn, PaymentIn
from verse.domain.enums import DealStage


async def test_deal_and_payment_totals(contacts, deals) -> None:
    contact_id = await contacts.create(contact_in("Buyer"))

    deal_id = await deals.create(
        contact_id, DealIn(title="Exclusive", amount_expected="500", currency="usd")
    )
    await deals.add_payment(deal_id, PaymentIn(amount="200", currency="usd"))
    await deals.add_payment(deal_id, PaymentIn(amount="100", currency="usd"))

    detail = await contacts.get(contact_id)
    assert detail.revenue == {"USD": Decimal("300.00")}
    assert detail.potential == {"USD": Decimal("500.00")}

    await deals.update(
        deal_id, DealIn(title="Exclusive", stage=DealStage.WON, amount_expected="500")
    )
    detail = await contacts.get(contact_id)
    assert detail.revenue == {"USD": Decimal("300.00")}
    assert detail.potential == {}


async def test_currencies_are_not_mixed(contacts, deals) -> None:
    contact_id = await contacts.create(contact_in("Euro Buyer"))
    first = await deals.create(contact_id, DealIn(title="A", amount_expected="100", currency="usd"))
    second = await deals.create(contact_id, DealIn(title="B", amount_expected="90", currency="eur"))
    await deals.add_payment(first, PaymentIn(amount="50", currency="usd"))
    await deals.add_payment(second, PaymentIn(amount="40", currency="eur"))

    detail = await contacts.get(contact_id)
    assert detail.revenue["USD"] == Decimal("50.00")
    assert detail.revenue["EUR"] == Decimal("40.00")
    assert detail.potential["USD"] == Decimal("100.00")
    assert detail.potential["EUR"] == Decimal("90.00")


async def test_deleted_deal_excluded(contacts, deals) -> None:
    contact_id = await contacts.create(contact_in("Lost"))
    deal_id = await deals.create(contact_id, DealIn(title="Lost deal", amount_expected="10"))
    await deals.delete(deal_id)

    detail = await contacts.get(contact_id)
    assert detail.deals == []
    assert detail.potential == {}
