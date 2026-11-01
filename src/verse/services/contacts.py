"""Сервис CRM: контакты, каналы, статусы, заметки.

Единственное место, где применяются правила:
* нормализация каналов и защита от дубликатов;
* взаимоисключение статусов внутри группы с `allows_multiple = false`;
* «один основной канал» на контакт;
* мягкое удаление и восстановление.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from verse.db.models import (
    Contact,
    ContactChannel,
    ContactNote,
    ContactStatus,
    Status,
)
from verse.db.repositories import contacts as repo
from verse.db.session import Database, transaction
from verse.domain.dto import (
    ChannelIn,
    ChannelView,
    ContactDetail,
    ContactIn,
    ContactRow,
    DealView,
    NoteView,
    Page,
    PaymentView,
    StatusRef,
)
from verse.domain.enums import AuditResult, ChannelType, DealStage, NoteAuthor
from verse.domain.filters import ContactFilter
from verse.domain.money import add_amount
from verse.domain.normalize import normalize_channel_value
from verse.errors import DuplicateChannelError, NotFoundError, ValidationError
from verse.services import audit as audit_service
from verse.services import statuses as status_service


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def contact_money(contact: Contact) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Фактический доход (платежи) и потенциальный (открытые сделки) — раздельно."""
    revenue: dict[str, Decimal] = {}
    potential: dict[str, Decimal] = {}
    for deal in contact.deals:
        if deal.deleted_at is not None:
            continue
        for payment in deal.payments:
            add_amount(revenue, payment.currency, payment.amount)
        if deal.stage is DealStage.OPEN and deal.amount_expected:
            add_amount(potential, deal.currency, deal.amount_expected)
    return revenue, potential


def _channel_views(contact: Contact) -> list[ChannelView]:
    return [
        ChannelView(
            id=channel.id,
            channel_type=channel.channel_type,
            raw_value=channel.raw_value,
            normalized_value=channel.normalized_value,
            label=channel.label,
            is_primary=channel.is_primary,
        )
        for channel in contact.channels
        if channel.deleted_at is None
    ]


def _status_views(contact: Contact) -> list[StatusRef]:
    refs: list[StatusRef] = []
    for link in contact.status_links:
        status: Status = link.status
        refs.append(
            StatusRef(
                id=status.id,
                name=status.name,
                color=status.color,
                group_name=status.group.name,
                group_slug=status.group.slug,
            )
        )
    return sorted(refs, key=lambda r: (r.group_name, r.name))


def to_row(contact: Contact) -> ContactRow:
    revenue, potential = contact_money(contact)
    return ContactRow(
        id=contact.id,
        display_name=contact.display_name,
        stage_name=contact.stage_name,
        source=contact.source,
        channels=_channel_views(contact),
        statuses=_status_views(contact),
        last_contact_at=contact.last_contact_at,
        next_action_at=contact.next_action_at,
        do_not_contact=contact.do_not_contact,
        is_deleted=contact.deleted_at is not None,
        notes=contact.notes,
        revenue=revenue,
        potential=potential,
        deals_count=len([d for d in contact.deals if d.deleted_at is None]),
    )


def to_detail(contact: Contact) -> ContactDetail:
    revenue, potential = contact_money(contact)
    deals = [
        DealView(
            id=deal.id,
            title=deal.title,
            stage=deal.stage,
            amount_expected=deal.amount_expected,
            currency=deal.currency,
            notes=deal.notes,
            payments=[
                PaymentView(
                    id=p.id,
                    amount=p.amount,
                    currency=p.currency,
                    paid_at=p.paid_at,
                    method=p.method,
                    notes=p.notes,
                )
                for p in deal.payments
            ],
        )
        for deal in contact.deals
        if deal.deleted_at is None
    ]
    return ContactDetail(
        id=contact.id,
        display_name=contact.display_name,
        real_name=contact.real_name,
        stage_name=contact.stage_name,
        source=contact.source,
        genres=contact.genres,
        references=contact.references,
        notes=contact.notes,
        do_not_contact=contact.do_not_contact,
        do_not_contact_reason=contact.do_not_contact_reason,
        last_contact_at=contact.last_contact_at,
        next_action_at=contact.next_action_at,
        created_at=contact.created_at,
        is_deleted=contact.deleted_at is not None,
        channels=_channel_views(contact),
        statuses=_status_views(contact),
        deals=deals,
        notes_history=[
            NoteView(
                id=note.id,
                body=note.body,
                author_kind=note.author_kind.value
                if hasattr(note.author_kind, "value")
                else str(note.author_kind),
                created_at=note.created_at,
            )
            for note in contact.note_entries
        ],
        revenue=revenue,
        potential=potential,
    )


def prepare_channels(channels: list[ChannelIn]) -> list[tuple[ChannelType, str, str, str | None, bool]]:
    """(type, raw, normalized, label, is_primary), без повторов."""
    prepared: list[tuple[ChannelType, str, str, str | None, bool]] = []
    seen: set[tuple[ChannelType, str]] = set()
    for item in channels:
        normalized = normalize_channel_value(item.channel_type, item.value)
        key = (item.channel_type, normalized)
        if key in seen:
            raise ValidationError(
                f"Канал {item.channel_type.label} «{item.value}» указан дважды"
            )
        seen.add(key)
        prepared.append((item.channel_type, item.value.strip(), normalized, item.label, item.is_primary))
    if prepared and not any(p[4] for p in prepared):
        first = prepared[0]
        prepared[0] = (first[0], first[1], first[2], first[3], True)
    return prepared


class ContactService:
    def __init__(self, db: Database) -> None:
        self.db = db

    # --- чтение -----------------------------------------------------------
    async def list(
        self,
        flt: ContactFilter | None = None,
        *,
        page: int = 1,
        page_size: int = 50,
        sort: str = "name",
        descending: bool = False,
    ) -> Page:
        flt = flt or ContactFilter()
        async with self.db.session() as session:
            total = await repo.count(session, flt)
            contacts = await repo.search(
                session, flt, page=page, page_size=page_size, sort=sort, descending=descending
            )
            return Page(
                items=[to_row(contact) for contact in contacts],
                total=total,
                page=page,
                page_size=page_size,
            )

    async def get(self, contact_id: uuid.UUID) -> ContactDetail:
        async with self.db.session() as session:
            contact = await repo.get(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Контакт {contact_id} не найден")
            return to_detail(contact)

    # --- запись -----------------------------------------------------------
    async def create(self, data: ContactIn) -> uuid.UUID:
        if not data.display_name or not data.display_name.strip():
            raise ValidationError("Имя контакта не может быть пустым")
        prepared = prepare_channels(data.channels)
        async with transaction(self.db.session_factory) as session:
            await self._assert_channels_free(session, prepared)
            contact = Contact(
                display_name=data.display_name,
                real_name=data.real_name,
                stage_name=data.stage_name,
                source=data.source,
                genres=data.genres,
                references=data.references,
                notes=data.notes,
                do_not_contact=data.do_not_contact,
                do_not_contact_reason=data.do_not_contact_reason,
                last_contact_at=_ensure_aware(data.last_contact_at),
                next_action_at=_ensure_aware(data.next_action_at),
            )
            session.add(contact)
            for channel_type, raw, normalized, label, is_primary in prepared:
                contact.channels.append(
                    ContactChannel(
                        channel_type=channel_type,
                        raw_value=raw,
                        normalized_value=normalized,
                        label=label,
                        is_primary=is_primary,
                    )
                )
            await self._apply_statuses(session, contact, data.status_ids)
            await session.flush()
            await audit_service.record(
                session,
                category="crm",
                event_type="contact.created",
                result=AuditResult.SUCCEEDED,
                entity_type="contact",
                entity_id=contact.id,
                message=f"Создан контакт «{contact.display_name}»",
                details={"channels": len(prepared), "statuses": len(data.status_ids)},
            )
            return contact.id

    async def update(self, contact_id: uuid.UUID, data: ContactIn) -> None:
        if not data.display_name or not data.display_name.strip():
            raise ValidationError("Имя контакта не может быть пустым")
        prepared = prepare_channels(data.channels)
        async with transaction(self.db.session_factory) as session:
            contact = await repo.get(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Контакт {contact_id} не найден")
            await self._assert_channels_free(session, prepared, exclude_contact_id=contact_id)
            await self._sync_channels(session, contact, prepared)

            contact.display_name = data.display_name
            contact.real_name = data.real_name
            contact.stage_name = data.stage_name
            contact.source = data.source
            contact.genres = data.genres
            contact.references = data.references
            contact.notes = data.notes
            contact.do_not_contact = data.do_not_contact
            contact.do_not_contact_reason = data.do_not_contact_reason
            contact.last_contact_at = _ensure_aware(data.last_contact_at)
            contact.next_action_at = _ensure_aware(data.next_action_at)

            await self._apply_statuses(session, contact, data.status_ids)
            await audit_service.record(
                session,
                category="crm",
                event_type="contact.updated",
                result=AuditResult.SUCCEEDED,
                entity_type="contact",
                entity_id=contact.id,
                message=f"Обновлён контакт «{contact.display_name}»",
                details={"channels": len([c for c in contact.channels if c.deleted_at is None])},
            )

    async def soft_delete(self, contact_id: uuid.UUID) -> None:
        async with transaction(self.db.session_factory) as session:
            contact = await repo.get(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Контакт {contact_id} не найден")
            contact.deleted_at = datetime.now(tz=UTC)
            await audit_service.record(
                session,
                category="crm",
                event_type="contact.trashed",
                result=AuditResult.SUCCEEDED,
                entity_type="contact",
                entity_id=contact.id,
                message=f"Контакт «{contact.display_name}» перемещён в корзину",
            )

    async def restore(self, contact_id: uuid.UUID) -> None:
        async with transaction(self.db.session_factory) as session:
            contact = await repo.get(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Контакт {contact_id} не найден")
            contact.deleted_at = None
            await audit_service.record(
                session,
                category="crm",
                event_type="contact.restored",
                result=AuditResult.SUCCEEDED,
                entity_type="contact",
                entity_id=contact.id,
                message=f"Контакт «{contact.display_name}» восстановлен",
            )

    async def purge(self, contact_id: uuid.UUID) -> None:
        """Окончательное удаление. Требует подтверждения в UI."""
        async with transaction(self.db.session_factory) as session:
            contact = await repo.get(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Контакт {contact_id} не найден")
            name = contact.display_name
            await session.delete(contact)
            await audit_service.record(
                session,
                category="crm",
                event_type="contact.deleted",
                result=AuditResult.SUCCEEDED,
                entity_type="contact",
                entity_id=contact_id,
                message=f"Контакт «{name}» удалён окончательно",
            )

    async def add_note(self, contact_id: uuid.UUID, body: str) -> None:
        body = body.strip()
        if not body:
            raise ValidationError("Заметка не может быть пустой")
        async with transaction(self.db.session_factory) as session:
            contact = await repo.get(session, contact_id)
            if contact is None:
                raise NotFoundError(f"Контакт {contact_id} не найден")
            session.add(ContactNote(contact_id=contact_id, body=body, author_kind=NoteAuthor.USER))
            await audit_service.record(
                session,
                category="crm",
                event_type="contact.note_added",
                result=AuditResult.SUCCEEDED,
                entity_type="contact",
                entity_id=contact_id,
                message="Добавлена заметка",
            )

    # --- внутреннее -------------------------------------------------------
    async def _assert_channels_free(
        self,
        session: AsyncSession,
        prepared: list[tuple[ChannelType, str, str, str | None, bool]],
        *,
        exclude_contact_id: uuid.UUID | None = None,
    ) -> None:
        for channel_type, _raw, normalized, _label, _primary in prepared:
            existing = await repo.find_by_channel(
                session, channel_type, normalized, exclude_contact_id=exclude_contact_id
            )
            if existing is not None:
                raise DuplicateChannelError(channel_type.value, normalized, existing.contact_id)

    async def _sync_channels(
        self,
        session: AsyncSession,
        contact: Contact,
        prepared: list[tuple[ChannelType, str, str, str | None, bool]],
    ) -> None:
        active = {c.id: c for c in contact.channels if c.deleted_at is None}
        desired = {(p[0], p[2]): p for p in prepared}
        current = {(c.channel_type, c.normalized_value): c for c in active.values()}

        now = datetime.now(tz=UTC)
        removed = [channel for key, channel in current.items() if key not in desired]
        for channel in removed:
            channel.deleted_at = now
            channel.is_primary = False
        if removed:
            await session.flush()

        primary_set = False
        for key, (channel_type, raw, normalized, label, is_primary) in desired.items():
            channel = current.get(key)
            if channel is None:
                channel = ContactChannel(
                    contact_id=contact.id,
                    channel_type=channel_type,
                    raw_value=raw,
                    normalized_value=normalized,
                    label=label,
                    is_primary=False,
                )
                contact.channels.append(channel)
                current[key] = channel
            else:
                channel.raw_value = raw
                channel.label = label
                channel.is_primary = False
            if is_primary and not primary_set:
                channel.is_primary = True
                primary_set = True

        if not primary_set and current:
            first_key = next(iter(desired))
            current[first_key].is_primary = True

    async def _apply_statuses(
        self, session: AsyncSession, contact: Contact, status_ids: list[uuid.UUID]
    ) -> None:
        desired = set(status_ids)
        statuses = await status_service.fetch_by_ids(session, desired)
        missing = desired - statuses.keys()
        if missing:
            raise ValidationError(f"Неизвестные статусы: {', '.join(map(str, missing))}")

        by_group: dict[uuid.UUID, list[Status]] = {}
        for status in statuses.values():
            by_group.setdefault(status.group_id, []).append(status)
        for group_statuses in by_group.values():
            if len(group_statuses) > 1 and not group_statuses[0].group.allows_multiple:
                raise ValidationError(
                    f"В группе «{group_statuses[0].group.name}» можно выбрать только один статус"
                )

        existing = {link.status_id: link for link in contact.status_links}
        for status_id, link in list(existing.items()):
            if status_id not in desired:
                contact.status_links.remove(link)

        for status_id in desired - existing.keys():
            contact.status_links.append(
                ContactStatus(status_id=status_id, group_id=statuses[status_id].group_id)
            )

    # --- массовые действия ------------------------------------------------
    async def bulk_trash(self, contact_ids: list[uuid.UUID]) -> int:
        if not contact_ids:
            return 0
        async with transaction(self.db.session_factory) as session:
            result = await session.execute(
                update(Contact)
                .where(Contact.id.in_(contact_ids), Contact.deleted_at.is_(None))
                .values(deleted_at=datetime.now(tz=UTC))
            )
            await audit_service.record(
                session,
                category="crm",
                event_type="contacts.trashed",
                result=AuditResult.SUCCEEDED,
                message=f"В корзину перемещено контактов: {result.rowcount}",
                details={"ids": [str(cid) for cid in contact_ids]},
            )
            return int(result.rowcount or 0)

    async def bulk_restore(self, contact_ids: list[uuid.UUID]) -> int:
        if not contact_ids:
            return 0
        async with transaction(self.db.session_factory) as session:
            result = await session.execute(
                update(Contact)
                .where(Contact.id.in_(contact_ids), Contact.deleted_at.is_not(None))
                .values(deleted_at=None)
            )
            await audit_service.record(
                session,
                category="crm",
                event_type="contacts.restored",
                result=AuditResult.SUCCEEDED,
                message=f"Восстановлено контактов: {result.rowcount}",
            )
            return int(result.rowcount or 0)

    async def bulk_purge(self, contact_ids: list[uuid.UUID]) -> int:
        if not contact_ids:
            return 0
        async with transaction(self.db.session_factory) as session:
            result = await session.execute(
                delete(Contact).where(Contact.id.in_(contact_ids))
            )
            await audit_service.record(
                session,
                category="crm",
                event_type="contacts.deleted",
                result=AuditResult.SUCCEEDED,
                message=f"Удалено окончательно контактов: {result.rowcount}",
                details={"ids": [str(cid) for cid in contact_ids]},
            )
            return int(result.rowcount or 0)

    async def set_dnc(
        self, contact_ids: list[uuid.UUID], value: bool, reason: str | None = None
    ) -> int:
        if not contact_ids:
            return 0
        async with transaction(self.db.session_factory) as session:
            result = await session.execute(
                update(Contact)
                .where(Contact.id.in_(contact_ids))
                .values(do_not_contact=value, do_not_contact_reason=reason)
            )
            await audit_service.record(
                session,
                category="crm",
                event_type="contacts.dnc_changed",
                result=AuditResult.SUCCEEDED,
                message=(
                    f"Do Not Contact {'установлен' if value else 'снят'}: {result.rowcount}"
                ),
            )
            return int(result.rowcount or 0)
