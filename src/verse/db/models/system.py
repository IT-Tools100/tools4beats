"""Системные модели: настройки, журнал событий, импорт/экспорт."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Identity, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verse.db.base import Base, Timestamps, UuidPk, enum_column
from verse.domain.enums import (
    AuditLevel,
    AuditResult,
    TransferDirection,
    TransferFormat,
    TransferState,
)


class AppSetting(Timestamps, Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AuditLog(Base):
    """Журнал событий. Секреты сюда не попадают (фильтр redaction)."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_occurred_at", "occurred_at"),
        Index("ix_audit_log_category_occurred_at", "category", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    level: Mapped[AuditLevel] = mapped_column(
        enum_column(AuditLevel), nullable=False, default=AuditLevel.INFO
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    result: Mapped[AuditResult | None] = mapped_column(enum_column(AuditResult))
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DataTransfer(UuidPk, Timestamps, Base):
    __tablename__ = "data_transfers"
    __table_args__ = (Index("ix_data_transfers_created_at", "created_at"),)

    direction: Mapped[TransferDirection] = mapped_column(
        enum_column(TransferDirection), nullable=False
    )
    format: Mapped[TransferFormat] = mapped_column(enum_column(TransferFormat), nullable=False)
    entity: Mapped[str] = mapped_column(String(60), nullable=False, default="contacts")
    file_path: Mapped[str | None] = mapped_column(Text)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[TransferState] = mapped_column(
        enum_column(TransferState), nullable=False, default=TransferState.RUNNING
    )
    error: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
