"""Агрегированная статистика для Dashboard (только реальные данные)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from verse.db.models import Contact, ContactStatus, Deal, Interaction, Payment, Status, StatusGroup
from verse.db.session import Database
from verse.domain.enums import DealStage


@dataclass(slots=True)
class DashboardStats:
    contacts_total: int = 0
    contacts_active: int = 0
    contacts_dnc: int = 0
    contacts_trashed: int = 0
    deals_open: int = 0
    revenue: dict[str, Decimal] = field(default_factory=dict)
    potential: dict[str, Decimal] = field(default_factory=dict)
    status_counts: list[tuple[str, str, int]] = field(default_factory=list)
    upcoming: list[tuple[str, datetime | None, str]] = field(default_factory=list)
    interactions_total: int = 0


async def dashboard(db: Database) -> DashboardStats:
    async with db.session() as session:
        contacts_total = int(await session.scalar(select(func.count(Contact.id))) or 0)
        contacts_active = int(
            await session.scalar(
                select(func.count(Contact.id)).where(Contact.deleted_at.is_(None))
            )
            or 0
        )
        contacts_dnc = int(
            await session.scalar(
                select(func.count(Contact.id)).where(
                    Contact.deleted_at.is_(None), Contact.do_not_contact.is_(True)
                )
            )
            or 0
        )
        contacts_trashed = contacts_total - contacts_active

        deals_open = int(
            await session.scalar(
                select(func.count(Deal.id)).where(
                    Deal.deleted_at.is_(None), Deal.stage == DealStage.OPEN
                )
            )
            or 0
        )

        revenue: dict[str, Decimal] = {}
        rows = await session.execute(
            select(Payment.currency, func.coalesce(func.sum(Payment.amount), 0)).group_by(
                Payment.currency
            )
        )
        for currency, amount in rows:
            revenue[str(currency)] = Decimal(amount)

        potential: dict[str, Decimal] = {}
        rows = await session.execute(
            select(Deal.currency, func.coalesce(func.sum(Deal.amount_expected), 0))
            .where(Deal.deleted_at.is_(None), Deal.stage == DealStage.OPEN)
            .group_by(Deal.currency)
        )
        for currency, amount in rows:
            potential[str(currency)] = Decimal(amount)

        status_rows = await session.execute(
            select(StatusGroup.name, Status.name, func.count(ContactStatus.contact_id))
            .join(Status, Status.id == ContactStatus.status_id)
            .join(StatusGroup, StatusGroup.id == Status.group_id)
            .join(Contact, Contact.id == ContactStatus.contact_id)
            .where(Contact.deleted_at.is_(None))
            .group_by(StatusGroup.name, Status.name)
            .order_by(func.count(ContactStatus.contact_id).desc())
            .limit(12)
        )
        status_counts = [(g, s, int(c)) for g, s, c in status_rows]

        upcoming_rows = await session.execute(
            select(Contact.id, Contact.next_action_at, Contact.display_name)
            .where(Contact.deleted_at.is_(None), Contact.next_action_at.is_not(None))
            .order_by(Contact.next_action_at)
            .limit(8)
        )
        upcoming = [(str(cid), dt, name) for cid, dt, name in upcoming_rows]

        interactions_total = int(
            await session.scalar(select(func.count(Interaction.id))) or 0
        )

    return DashboardStats(
        contacts_total=contacts_total,
        contacts_active=contacts_active,
        contacts_dnc=contacts_dnc,
        contacts_trashed=contacts_trashed,
        deals_open=deals_open,
        revenue=revenue,
        potential=potential,
        status_counts=status_counts,
        upcoming=upcoming,
        interactions_total=interactions_total,
    )
