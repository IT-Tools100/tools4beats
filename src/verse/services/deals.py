"""Сделки и платежи."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from verse.db.models import Deal, Payment
from verse.db.session import Database, transaction
from verse.domain.dto import DealIn, PaymentIn
from verse.domain.enums import AuditResult, DealStage
from verse.errors import NotFoundError, ValidationError
from verse.services import audit as audit_service


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


class DealService:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, contact_id: uuid.UUID, data: DealIn) -> uuid.UUID:
        async with transaction(self.db.session_factory) as session:
            deal = Deal(
                contact_id=contact_id,
                title=data.title,
                stage=data.stage,
                amount_expected=data.amount_expected,
                currency=data.currency,
                notes=data.notes,
                closed_at=datetime.now(tz=UTC) if data.stage is not DealStage.OPEN else None,
            )
            session.add(deal)
            await session.flush()
            await audit_service.record(
                session,
                category="crm",
                event_type="deal.created",
                result=AuditResult.SUCCEEDED,
                entity_type="deal",
                entity_id=deal.id,
                message=f"Создана сделка «{data.title}»",
                details={"contact_id": str(contact_id)},
            )
            return deal.id

    async def update(self, deal_id: uuid.UUID, data: DealIn) -> None:
        async with transaction(self.db.session_factory) as session:
            deal = await session.get(Deal, deal_id)
            if deal is None or deal.deleted_at is not None:
                raise NotFoundError(f"Сделка {deal_id} не найдена")
            deal.title = data.title
            deal.stage = data.stage
            deal.amount_expected = data.amount_expected
            deal.currency = data.currency
            deal.notes = data.notes
            deal.closed_at = (
                datetime.now(tz=UTC) if data.stage is not DealStage.OPEN else None
            )
            await audit_service.record(
                session,
                category="crm",
                event_type="deal.updated",
                result=AuditResult.SUCCEEDED,
                entity_type="deal",
                entity_id=deal.id,
                message=f"Обновлена сделка «{deal.title}»",
            )

    async def delete(self, deal_id: uuid.UUID) -> None:
        async with transaction(self.db.session_factory) as session:
            deal = await session.get(Deal, deal_id)
            if deal is None:
                raise NotFoundError(f"Сделка {deal_id} не найдена")
            deal.deleted_at = datetime.now(tz=UTC)
            await audit_service.record(
                session,
                category="crm",
                event_type="deal.deleted",
                result=AuditResult.SUCCEEDED,
                entity_type="deal",
                entity_id=deal_id,
                message=f"Удалена сделка «{deal.title}»",
            )

    async def add_payment(self, deal_id: uuid.UUID, data: PaymentIn) -> uuid.UUID:
        if data.amount <= 0:
            raise ValidationError("Сумма платежа должна быть больше нуля")
        async with transaction(self.db.session_factory) as session:
            deal = await session.get(Deal, deal_id)
            if deal is None or deal.deleted_at is not None:
                raise NotFoundError(f"Сделка {deal_id} не найдена")
            payment = Payment(
                deal_id=deal_id,
                amount=data.amount,
                currency=data.currency,
                paid_at=_aware(data.paid_at) or datetime.now(tz=UTC),
                method=data.method,
                notes=data.notes,
            )
            session.add(payment)
            await session.flush()
            await audit_service.record(
                session,
                category="crm",
                event_type="payment.created",
                result=AuditResult.SUCCEEDED,
                entity_type="deal",
                entity_id=deal_id,
                message=f"Платёж {data.amount} {data.currency} по сделке «{deal.title}»",
            )
            return payment.id

    async def delete_payment(self, payment_id: uuid.UUID) -> None:
        async with transaction(self.db.session_factory) as session:
            payment = await session.get(Payment, payment_id)
            if payment is None:
                raise NotFoundError(f"Платёж {payment_id} не найден")
            await session.delete(payment)
            await audit_service.record(
                session,
                category="crm",
                event_type="payment.deleted",
                result=AuditResult.SUCCEEDED,
                entity_type="deal",
                entity_id=payment.deal_id,
                message="Удалён платёж",
            )
