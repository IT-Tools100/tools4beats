"""Все ORM-модели в одном месте — чтобы Alembic и приложение видели metadata."""

from verse.db.models.crm import (
    Contact,
    ContactChannel,
    ContactNote,
    ContactReminder,
    ContactStatus,
    Deal,
    Exclusion,
    Interaction,
    Payment,
    Status,
    StatusGroup,
)
from verse.db.models.system import AppSetting, AuditLog, DataTransfer

__all__ = [
    "AppSetting",
    "AuditLog",
    "Contact",
    "ContactChannel",
    "ContactNote",
    "ContactReminder",
    "ContactStatus",
    "DataTransfer",
    "Deal",
    "Exclusion",
    "Interaction",
    "Payment",
    "Status",
    "StatusGroup",
]
