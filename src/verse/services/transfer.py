"""Импорт и экспорт контактов (CSV).

Правила:
* маппинг колонок задаётся явно, автоподбор — только черновик;
* повторный импорт того же файла не создаёт дубликатов (ищем по каналам);
* если строка совпала с несколькими контактами — конфликт, строка не применяется;
* результат фиксируется в `data_transfers` и `audit_log`.
"""

from __future__ import annotations

import csv
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from verse.db.models import Contact, ContactChannel, ContactStatus, DataTransfer, Deal, Status
from verse.db.repositories import contacts as repo
from verse.db.session import Database, transaction
from verse.domain.dto import ImportReport
from verse.domain.enums import (
    AuditResult,
    ChannelType,
    ContactSource,
    TransferDirection,
    TransferFormat,
    TransferState,
)
from verse.domain.money import format_amounts
from verse.domain.normalize import normalize_channel_value
from verse.errors import ValidationError
from verse.services import audit as audit_service
from verse.services.contacts import contact_money

FIELD_LABELS: dict[str, str] = {
    "display_name": "Имя",
    "stage_name": "Псевдоним",
    "real_name": "Настоящее имя",
    "source": "Источник",
    "email": "Email",
    "phone": "Телефон",
    "instagram": "Instagram",
    "spotify": "Spotify",
    "youtube": "YouTube",
    "soundcloud": "SoundCloud",
    "discord": "Discord",
    "telegram": "Telegram",
    "genres": "Жанры",
    "notes": "Заметки",
    "statuses": "Статусы",
}

CHANNEL_FIELDS: dict[str, ChannelType] = {
    "email": ChannelType.EMAIL,
    "phone": ChannelType.PHONE,
    "instagram": ChannelType.INSTAGRAM,
    "spotify": ChannelType.SPOTIFY,
    "youtube": ChannelType.YOUTUBE,
    "soundcloud": ChannelType.SOUNDCLOUD,
    "discord": ChannelType.DISCORD,
    "telegram": ChannelType.TELEGRAM,
}

ALIASES: dict[str, tuple[str, ...]] = {
    "display_name": ("name", "display_name", "displayname", "artist", "contact", "имя", "контакт", "артист"),
    "stage_name": ("stage_name", "stagename", "nickname", "nick", "псевдоним", "ник"),
    "real_name": ("real_name", "realname", "full_name", "fullname", "фио"),
    "source": ("source", "источник"),
    "email": ("email", "e_mail", "mail", "почта", "email_address"),
    "phone": ("phone", "tel", "telephone", "телефон", "номер"),
    "instagram": ("instagram", "insta", "ig", "instagram_url", "инстаграм"),
    "spotify": ("spotify", "spotify_url", "spotify_id", "спотифай"),
    "youtube": ("youtube", "yt", "youtube_url", "ютуб"),
    "soundcloud": ("soundcloud", "sc", "soundcloud_url", "саундклауд"),
    "discord": ("discord", "discord_tag", "дискорд"),
    "telegram": ("telegram", "tg", "телеграм"),
    "genres": ("genres", "genre", "жанр", "жанры"),
    "notes": ("notes", "note", "comment", "commentary", "заметки", "комментарий"),
    "statuses": ("statuses", "status", "статус", "статусы"),
}

EXPORT_COLUMNS: list[str] = [
    "display_name",
    "stage_name",
    "real_name",
    "source",
    "email",
    "phone",
    "instagram",
    "spotify",
    "youtube",
    "soundcloud",
    "discord",
    "telegram",
    "genres",
    "notes",
    "statuses",
    "do_not_contact",
    "last_contact_at",
    "next_action_at",
    "revenue",
    "potential",
]


# ---------------------------------------------------------------------------
# Чтение
# ---------------------------------------------------------------------------


def _detect_delimiter(sample: str) -> str:
    counts = {delimiter: sample.count(delimiter) for delimiter in (",", ";", "\t")}
    return max(counts, key=counts.get) if any(counts.values()) else ","


def _open_text(path: Path) -> TextIO:
    for encoding in ("utf-8-sig", "cp1251", "utf-8"):
        try:
            handle = path.open("r", encoding=encoding, newline="")
            handle.read(0)
            return handle
        except UnicodeDecodeError:
            continue
    return path.open("r", encoding="latin-1", newline="")


def read_table(path: str | Path) -> tuple[list[str], list[list[str]]]:
    path = Path(path)
    if not path.exists():
        raise ValidationError(f"Файл не найден: {path}")
    with _open_text(path) as handle:
        head = handle.readline()
        handle.seek(0)
        delimiter = _detect_delimiter(head)
        rows = [row for row in csv.reader(handle, delimiter=delimiter)]
    if not rows:
        raise ValidationError("Файл пуст")
    headers = [h.strip() for h in rows[0]]
    return headers, rows[1:]


def normalize_header(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("ё", "е")
        .replace("-", "_")
        .replace(" ", "_")
        .replace(".", "")
    )


def auto_mapping(headers: Sequence[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    normalized = [normalize_header(h) for h in headers]
    for field_name, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field_name] = normalized.index(alias)
                break
    return mapping


@dataclass(slots=True)
class Preview:
    headers: list[str]
    rows: list[list[str]]
    mapping: dict[str, int]
    total_rows: int


def preview(path: str | Path, limit: int = 10) -> Preview:
    headers, rows = read_table(path)
    return Preview(
        headers=headers,
        rows=rows[:limit],
        mapping=auto_mapping(headers),
        total_rows=len(rows),
    )


# ---------------------------------------------------------------------------
# Импорт
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Row:
    values: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str:
        return (self.values.get(key) or "").strip()


def _parse_row(row: Sequence[str], mapping: dict[str, int]) -> _Row:
    values: dict[str, str] = {}
    for field_name, index in mapping.items():
        if index < len(row):
            values[field_name] = (row[index] or "").strip()
    return _Row(values)


def _parse_source(value: str) -> ContactSource:
    value = value.strip().lower()
    for source in ContactSource:
        if source.value == value:
            return source
    return ContactSource.IMPORT


async def _resolve_existing(
    session: AsyncSession, channels: list[tuple[ChannelType, str]]
) -> tuple[list[uuid.UUID], list[tuple[ChannelType, str]]]:
    contact_ids: set[uuid.UUID] = set()
    free: list[tuple[ChannelType, str]] = []
    for channel_type, normalized in channels:
        found = await repo.find_by_channel(session, channel_type, normalized)
        if found is None:
            free.append((channel_type, normalized))
        else:
            contact_ids.add(found.contact_id)
    return list(contact_ids), free


async def _statuses_by_name(session: AsyncSession) -> dict[str, Status]:
    result = await session.execute(select(Status).options(selectinload(Status.group)))
    mapping: dict[str, Status] = {}
    for status in result.scalars().unique():
        mapping[status.name.strip().lower()] = status
        mapping[status.slug.lower()] = status
    return mapping


def _mark_primary(contact: Contact) -> None:
    active = [c for c in contact.channels if c.deleted_at is None]
    if active and not any(c.is_primary for c in active):
        active[0].is_primary = True


def _apply_status_names(contact: Contact, raw: str | None, statuses: dict[str, Status]) -> None:
    if not raw:
        return
    names = [part.strip().lower() for part in raw.replace(";", ",").split(",") if part.strip()]
    for name in names:
        status = statuses.get(name)
        if status is None:
            continue
        if any(link.status_id == status.id for link in contact.status_links):
            continue
        if not status.group.allows_multiple and any(
            link.group_id == status.group_id for link in contact.status_links
        ):
            continue
        contact.status_links.append(ContactStatus(status_id=status.id, group_id=status.group_id))


def _create_contact(
    session: AsyncSession,
    data: _Row,
    channels: list[tuple[ChannelType, str, str]],
    statuses: dict[str, Status],
    default_source: ContactSource,
) -> Contact:
    contact = Contact(
        display_name=data.get("display_name")[:300],
        stage_name=data.get("stage_name")[:300] or None,
        real_name=data.get("real_name")[:300] or None,
        genres=data.get("genres") or None,
        notes=data.get("notes") or None,
        source=_parse_source(data.get("source")) if data.get("source") else default_source,
    )
    for channel_type, raw, normalized in channels:
        contact.channels.append(
            ContactChannel(channel_type=channel_type, raw_value=raw, normalized_value=normalized)
        )
    _mark_primary(contact)
    _apply_status_names(contact, data.get("statuses"), statuses)
    session.add(contact)
    return contact


async def _update_contact(
    session: AsyncSession,
    contact_id: uuid.UUID,
    data: _Row,
    free_channels: list[tuple[ChannelType, str]],
    channels: list[tuple[ChannelType, str, str]],
    statuses: dict[str, Status],
    default_source: ContactSource,
) -> bool:
    contact = await repo.get(session, contact_id)
    if contact is None:
        raise ValidationError(f"Контакт {contact_id} не найден")
    changed = False

    for field_name in ("stage_name", "real_name", "genres", "notes"):
        value = data.get(field_name)
        if not value:
            continue
        current = getattr(contact, field_name)
        if current != value:
            setattr(
                contact,
                field_name,
                value[:300] if field_name in ("stage_name", "real_name") else value,
            )
            changed = True

    if contact.source is ContactSource.IMPORT:
        source = _parse_source(data.get("source")) if data.get("source") else default_source
        if contact.source != source:
            contact.source = source
            changed = True

    free_keys = set(free_channels)
    for channel_type, raw, normalized in channels:
        if (channel_type, normalized) not in free_keys:
            continue
        contact.channels.append(
            ContactChannel(channel_type=channel_type, raw_value=raw, normalized_value=normalized)
        )
        changed = True

    if not any(c.is_primary for c in contact.channels if c.deleted_at is None):
        _mark_primary(contact)
        changed = True

    if data.get("statuses"):
        before = {link.status_id for link in contact.status_links}
        _apply_status_names(contact, data.get("statuses"), statuses)
        changed = changed or before != {link.status_id for link in contact.status_links}

    return changed


async def import_contacts(
    db: Database,
    path: str | Path,
    mapping: dict[str, int] | None = None,
    *,
    default_source: ContactSource = ContactSource.IMPORT,
    limit: int | None = None,
) -> ImportReport:
    path = Path(path)
    headers, rows = read_table(path)
    mapping = mapping or auto_mapping(headers)
    if "display_name" not in mapping:
        raise ValidationError("Не выбрана колонка с именем контакта")

    report = ImportReport(total_rows=len(rows))
    if limit:
        rows = rows[:limit]

    async with transaction(db.session_factory) as session:
        statuses = await _statuses_by_name(session)
        transfer = DataTransfer(
            direction=TransferDirection.IMPORT,
            format=TransferFormat.CSV,
            entity="contacts",
            file_path=str(path),
            mapping={k: headers[v] if v < len(headers) else str(v) for k, v in mapping.items()},
        )
        session.add(transfer)
        await session.flush()

        for line_no, raw_row in enumerate(rows, start=2):
            if not any(cell.strip() for cell in raw_row):
                continue
            data = _parse_row(raw_row, mapping)
            name = data.get("display_name")
            if not name:
                report.errors.append(f"Строка {line_no}: пустое имя — пропущена")
                continue

            channels: list[tuple[ChannelType, str, str]] = []
            bad = False
            for field_name, channel_type in CHANNEL_FIELDS.items():
                value = data.get(field_name)
                if not value:
                    continue
                try:
                    normalized = normalize_channel_value(channel_type, value)
                except ValidationError as exc:
                    report.errors.append(f"Строка {line_no}: {exc}")
                    bad = True
                    continue
                channels.append((channel_type, value, normalized))
            if bad:
                continue

            contact_ids, free_channels = await _resolve_existing(
                session, [(c[0], c[2]) for c in channels]
            )

            if len(contact_ids) > 1:
                report.conflicts += 1
                report.errors.append(
                    f"Строка {line_no}: «{name}» совпал с несколькими контактами "
                    f"({len(contact_ids)}) — требуется ручное слияние"
                )
                continue

            try:
                if contact_ids:
                    changed = await _update_contact(
                        session, contact_ids[0], data, free_channels, channels, statuses, default_source
                    )
                    if changed:
                        report.updated += 1
                    else:
                        report.unchanged += 1
                else:
                    _create_contact(session, data, channels, statuses, default_source)
                    await session.flush()
                    report.created += 1
            except ValidationError as exc:
                report.errors.append(f"Строка {line_no}: {exc}")

        transfer.stats = report.model_dump(mode="json")
        transfer.state = TransferState.COMPLETED
        transfer.finished_at = datetime.now(tz=UTC)
        await audit_service.record(
            session,
            category="import",
            event_type="contacts.imported",
            result=AuditResult.SUCCEEDED,
            entity_type="data_transfer",
            entity_id=transfer.id,
            message=report.summary(),
            details=report.model_dump(mode="json"),
        )
        return report


# ---------------------------------------------------------------------------
# Экспорт
# ---------------------------------------------------------------------------


async def export_contacts(
    db: Database,
    path: str | Path,
    contact_ids: Iterable[uuid.UUID] | None = None,
) -> int:
    ids = list(contact_ids) if contact_ids else None

    async with transaction(db.session_factory) as session:
        stmt = (
            select(Contact)
            .where(Contact.deleted_at.is_(None))
            .order_by(Contact.display_name)
            .options(
                selectinload(Contact.channels),
                selectinload(Contact.status_links).selectinload(ContactStatus.status),
                selectinload(Contact.deals).selectinload(Deal.payments),
            )
        )
        if ids:
            stmt = stmt.where(Contact.id.in_(ids))
        contacts = list((await session.execute(stmt)).scalars().unique().all())

        transfer = DataTransfer(
            direction=TransferDirection.EXPORT,
            format=TransferFormat.CSV,
            entity="contacts",
            file_path=str(path),
        )
        session.add(transfer)
        await session.flush()

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
            writer.writeheader()
            for contact in contacts:
                revenue, potential = contact_money(contact)
                row: dict[str, str] = {column: "" for column in EXPORT_COLUMNS}
                row["display_name"] = contact.display_name
                row["stage_name"] = contact.stage_name or ""
                row["real_name"] = contact.real_name or ""
                row["source"] = contact.source.value
                row["genres"] = contact.genres or ""
                row["notes"] = contact.notes or ""
                row["do_not_contact"] = "yes" if contact.do_not_contact else "no"
                row["last_contact_at"] = (
                    contact.last_contact_at.isoformat() if contact.last_contact_at else ""
                )
                row["next_action_at"] = (
                    contact.next_action_at.isoformat() if contact.next_action_at else ""
                )
                row["statuses"] = ", ".join(link.status.name for link in contact.status_links)
                row["revenue"] = format_amounts(revenue)
                row["potential"] = format_amounts(potential)
                by_type: dict[ChannelType, list[str]] = {}
                for channel in contact.channels:
                    if channel.deleted_at is not None:
                        continue
                    by_type.setdefault(channel.channel_type, []).append(channel.normalized_value)
                for field_name, channel_type in CHANNEL_FIELDS.items():
                    values = by_type.get(channel_type)
                    if values:
                        row[field_name] = values[0]
                writer.writerow(row)

        transfer.stats = {"exported": len(contacts)}
        transfer.state = TransferState.COMPLETED
        transfer.finished_at = datetime.now(tz=UTC)
        await audit_service.record(
            session,
            category="export",
            event_type="contacts.exported",
            result=AuditResult.SUCCEEDED,
            entity_type="data_transfer",
            entity_id=transfer.id,
            message=f"Экспортировано контактов: {len(contacts)}",
            details={"path": str(path)},
        )
        return len(contacts)
