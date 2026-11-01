"""Запросы по контактам. Единственное место, где строится SQL для CRM-списка."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from verse.db.models import Contact, ContactChannel, ContactStatus, Deal, Status
from verse.domain.enums import PHONE_CHANNELS, ChannelType
from verse.domain.filters import ContactFilter

_EAGER = (
    selectinload(Contact.channels),
    selectinload(Contact.status_links).selectinload(ContactStatus.status).selectinload(Status.group),
    selectinload(Contact.deals).selectinload(Deal.payments),
    selectinload(Contact.note_entries),
)


def _like(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def build_conditions(flt: ContactFilter) -> list:
    conditions = []
    if flt.only_deleted:
        conditions.append(Contact.deleted_at.is_not(None))
    elif not flt.include_deleted:
        conditions.append(Contact.deleted_at.is_(None))

    if flt.query:
        raw_query = flt.query.strip()
        pattern = _like(raw_query)
        # Хэндлы хранятся без "@": пользователь ищет "@nick", ищем "nick".
        handle_patterns = [_like(raw_query)]
        if raw_query.startswith("@") and len(raw_query) > 1:
            handle_patterns.append(_like(raw_query[1:]))
        channel_match = (
            select(ContactChannel.contact_id)
            .where(
                ContactChannel.deleted_at.is_(None),
                or_(
                    *[
                        ContactChannel.normalized_value.ilike(handle, escape="\\")
                        for handle in handle_patterns
                    ]
                ),
            )
            .scalar_subquery()
        )
        conditions.append(
            or_(
                Contact.display_name.ilike(pattern, escape="\\"),
                Contact.stage_name.ilike(pattern, escape="\\"),
                Contact.real_name.ilike(pattern, escape="\\"),
                Contact.genres.ilike(pattern, escape="\\"),
                Contact.notes.ilike(pattern, escape="\\"),
                Contact.id.in_(channel_match),
            )
        )

    if flt.status_ids:
        conditions.append(
            Contact.id.in_(
                select(ContactStatus.contact_id).where(
                    ContactStatus.status_id.in_(flt.status_ids)
                )
            )
        )

    if flt.channel_type is not None:
        conditions.append(
            Contact.id.in_(
                select(ContactChannel.contact_id).where(
                    ContactChannel.channel_type == flt.channel_type,
                    ContactChannel.deleted_at.is_(None),
                )
            )
        )

    if flt.source is not None:
        conditions.append(Contact.source == flt.source)

    if flt.only_dnc:
        conditions.append(Contact.do_not_contact.is_(True))

    email_exists = (
        select(ContactChannel.contact_id)
        .where(
            ContactChannel.channel_type == ChannelType.EMAIL,
            ContactChannel.deleted_at.is_(None),
        )
        .scalar_subquery()
    )
    phone_exists = (
        select(ContactChannel.contact_id)
        .where(
            ContactChannel.channel_type.in_(tuple(PHONE_CHANNELS)),
            ContactChannel.deleted_at.is_(None),
        )
        .scalar_subquery()
    )
    if flt.has_email is True:
        conditions.append(Contact.id.in_(email_exists))
    elif flt.has_email is False:
        conditions.append(Contact.id.not_in(email_exists))
    if flt.has_phone is True:
        conditions.append(Contact.id.in_(phone_exists))
    elif flt.has_phone is False:
        conditions.append(Contact.id.not_in(phone_exists))

    return conditions


def _apply_sort(stmt: Select, sort: str, descending: bool) -> Select:
    mapping = {
        "name": Contact.display_name,
        "last_contact": Contact.last_contact_at,
        "next_action": Contact.next_action_at,
        "created": Contact.created_at,
    }
    column = mapping.get(sort, Contact.display_name)
    return stmt.order_by(column.desc().nullslast() if descending else column.asc().nullsfirst())


async def count(session: AsyncSession, flt: ContactFilter) -> int:
    stmt = select(func.count(Contact.id))
    for condition in build_conditions(flt):
        stmt = stmt.where(condition)
    return int(await session.scalar(stmt) or 0)


async def search(
    session: AsyncSession,
    flt: ContactFilter,
    *,
    page: int = 1,
    page_size: int = 50,
    sort: str = "name",
    descending: bool = False,
) -> list[Contact]:
    stmt = select(Contact)
    for condition in build_conditions(flt):
        stmt = stmt.where(condition)
    stmt = _apply_sort(stmt, sort, descending)
    stmt = stmt.limit(page_size).offset(max(0, page - 1) * page_size)
    stmt = stmt.options(*_EAGER)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def get(session: AsyncSession, contact_id: uuid.UUID) -> Contact | None:
    stmt = select(Contact).where(Contact.id == contact_id).options(*_EAGER)
    result = await session.execute(stmt)
    return result.scalars().unique().one_or_none()


async def find_by_channel(
    session: AsyncSession,
    channel_type: ChannelType,
    normalized_value: str,
    *,
    exclude_contact_id: uuid.UUID | None = None,
) -> ContactChannel | None:
    stmt = select(ContactChannel).where(
        ContactChannel.channel_type == channel_type,
        ContactChannel.normalized_value == normalized_value,
        ContactChannel.deleted_at.is_(None),
    )
    if exclude_contact_id is not None:
        stmt = stmt.where(ContactChannel.contact_id != exclude_contact_id)
    result = await session.execute(stmt.limit(1))
    return result.scalar_one_or_none()


async def channels_for_contacts(
    session: AsyncSession, contact_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[ContactChannel]]:
    if not contact_ids:
        return {}
    stmt = select(ContactChannel).where(
        ContactChannel.contact_id.in_(contact_ids), ContactChannel.deleted_at.is_(None)
    )
    result = await session.execute(stmt)
    grouped: dict[uuid.UUID, list[ContactChannel]] = {}
    for channel in result.scalars():
        grouped.setdefault(channel.contact_id, []).append(channel)
    return grouped
