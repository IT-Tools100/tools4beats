"""Журнал событий (audit_log)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verse.db.models import AuditLog
from verse.domain.dto import AuditEntry
from verse.domain.enums import AuditLevel, AuditResult
from verse.security.redaction import redact, redact_value


async def record(
    session: AsyncSession,
    *,
    category: str,
    event_type: str,
    level: AuditLevel = AuditLevel.INFO,
    result: AuditResult | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            category=category,
            event_type=event_type,
            level=level,
            result=result,
            entity_type=entity_type,
            entity_id=entity_id,
            job_id=job_id,
            message=redact(message) if message else None,
            details=redact_value(details or {}),
        )
    )
    await session.flush()


async def list_entries(
    session: AsyncSession,
    *,
    limit: int = 200,
    category: str | None = None,
    level: str | None = None,
    search: str | None = None,
) -> list[AuditEntry]:
    stmt = select(AuditLog).order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc()).limit(limit)
    if category:
        stmt = stmt.where(AuditLog.category == category)
    if level:
        stmt = stmt.where(AuditLog.level == level)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(AuditLog.event_type.ilike(pattern))
    result = await session.execute(stmt)
    return [
        AuditEntry(
            id=row.id,
            occurred_at=row.occurred_at,
            level=row.level.value if hasattr(row.level, "value") else str(row.level),
            category=row.category,
            event_type=row.event_type,
            message=row.message,
            result=row.result.value if row.result is not None else None,
            entity_type=row.entity_type,
        )
        for row in result.scalars()
    ]


async def latest(session: AsyncSession) -> datetime | None:
    return await session.scalar(select(AuditLog.occurred_at).order_by(AuditLog.id.desc()).limit(1))
