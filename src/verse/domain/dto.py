"""DTO (Pydantic) для обмена между UI и ядром.

Ядро не знает про Qt, UI не знает про ORM — обмен идёт через эти схемы.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from verse.domain.enums import ChannelType, ContactSource, DealStage

MAX_NAME = 300


class ChannelIn(BaseModel):
    channel_type: ChannelType
    value: str = Field(min_length=1, max_length=500)
    label: str | None = Field(default=None, max_length=60)
    is_primary: bool = False

    @field_validator("value")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Значение канала не может быть пустым")
        return value


class ContactIn(BaseModel):
    """Данные для создания или полного обновления контакта."""

    display_name: str = Field(min_length=1, max_length=MAX_NAME)
    real_name: str | None = Field(default=None, max_length=MAX_NAME)
    stage_name: str | None = Field(default=None, max_length=MAX_NAME)
    source: ContactSource = ContactSource.MANUAL
    genres: str | None = None
    references: str | None = None
    notes: str | None = None
    do_not_contact: bool = False
    do_not_contact_reason: str | None = None
    last_contact_at: datetime | None = None
    next_action_at: datetime | None = None
    channels: list[ChannelIn] = Field(default_factory=list)
    status_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Имя контакта не может быть пустым")
        return value

    @field_validator("stage_name", "real_name")
    @classmethod
    def _strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ChannelView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel_type: ChannelType
    raw_value: str
    normalized_value: str
    label: str | None
    is_primary: bool


class StatusRef(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    group_name: str
    group_slug: str


class DealIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    stage: DealStage = DealStage.OPEN
    amount_expected: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    paid_at: datetime | None = None
    method: str | None = None
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.upper()


class PaymentView(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: str
    paid_at: datetime
    method: str | None
    notes: str | None


class DealView(BaseModel):
    id: uuid.UUID
    title: str
    stage: DealStage
    amount_expected: Decimal | None
    currency: str
    notes: str | None
    payments: list[PaymentView] = Field(default_factory=list)

    @property
    def paid_total(self) -> Decimal:
        return sum((p.amount for p in self.payments), Decimal("0"))


class ContactRow(BaseModel):
    """Строка таблицы CRM (агрегированные значения для списка)."""

    id: uuid.UUID
    display_name: str
    stage_name: str | None
    source: ContactSource
    channels: list[ChannelView]
    statuses: list[StatusRef]
    last_contact_at: datetime | None
    next_action_at: datetime | None
    do_not_contact: bool
    is_deleted: bool
    notes: str | None
    revenue: dict[str, Decimal] = Field(default_factory=dict)
    potential: dict[str, Decimal] = Field(default_factory=dict)
    deals_count: int = 0


class NoteView(BaseModel):
    id: uuid.UUID
    body: str
    author_kind: str
    created_at: datetime


class ContactDetail(BaseModel):
    id: uuid.UUID
    display_name: str
    real_name: str | None
    stage_name: str | None
    source: ContactSource
    genres: str | None
    references: str | None
    notes: str | None
    do_not_contact: bool
    do_not_contact_reason: str | None
    last_contact_at: datetime | None
    next_action_at: datetime | None
    created_at: datetime
    is_deleted: bool
    channels: list[ChannelView]
    statuses: list[StatusRef]
    deals: list[DealView]
    notes_history: list[NoteView] = Field(default_factory=list)
    revenue: dict[str, Decimal] = Field(default_factory=dict)
    potential: dict[str, Decimal] = Field(default_factory=dict)


class Page(BaseModel):
    items: list[ContactRow]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, (self.total + self.page_size - 1) // self.page_size)


class StatusOption(BaseModel):
    id: uuid.UUID
    name: str
    color: str
    group_name: str
    group_slug: str
    allows_multiple: bool


class StatusGroupView(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    color: str
    allows_multiple: bool
    statuses: list[StatusOption]


class AuditEntry(BaseModel):
    id: int
    occurred_at: datetime
    level: str
    category: str
    event_type: str
    message: str | None
    result: str | None
    entity_type: str | None


class ImportReport(BaseModel):
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    conflicts: int = 0
    errors: list[str] = Field(default_factory=list)
    total_rows: int = 0

    def summary(self) -> str:
        return (
            f"Строк: {self.total_rows}. Создано: {self.created}. "
            f"Обновлено: {self.updated}. Без изменений: {self.unchanged}. "
            f"Конфликтов: {self.conflicts}. Ошибок: {len(self.errors)}."
        )
