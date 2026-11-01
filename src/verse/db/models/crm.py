"""CRM-модели: контакты, каналы, статусы, заметки, напоминания, история."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from verse.db.base import Base, Timestamps, UuidPk, enum_column
from verse.domain.enums import (
    ChannelType,
    ContactSource,
    DealStage,
    Direction,
    NoteAuthor,
    ReminderState,
)


class StatusGroup(UuidPk, Timestamps, Base):
    __tablename__ = "status_groups"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#6b7280")
    allows_multiple: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    statuses: Mapped[list["Status"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="Status.sort_order"
    )


class Status(UuidPk, Timestamps, Base):
    __tablename__ = "statuses"
    __table_args__ = (
        UniqueConstraint("group_id", "slug", name="uq_statuses_group_id_slug"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("status_groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#6b7280")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    group: Mapped[StatusGroup] = relationship(back_populates="statuses")


class Contact(UuidPk, Timestamps, Base):
    __tablename__ = "contacts"

    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    real_name: Mapped[str | None] = mapped_column(String(300))
    stage_name: Mapped[str | None] = mapped_column(String(300))
    source: Mapped[ContactSource] = mapped_column(
        enum_column(ContactSource), nullable=False, default=ContactSource.MANUAL
    )
    source_ref: Mapped[str | None] = mapped_column(Text)
    genres: Mapped[str | None] = mapped_column(Text)
    references: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    custom: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_contact_reason: Mapped[str | None] = mapped_column(Text)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    channels: Mapped[list["ContactChannel"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ContactChannel.created_at",
    )
    status_links: Mapped[list["ContactStatus"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )
    note_entries: Mapped[list["ContactNote"]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ContactNote.created_at.desc()",
    )
    reminders: Mapped[list["ContactReminder"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )
    deals: Mapped[list["Deal"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_contacts_deleted_at", "deleted_at"),
        Index("ix_contacts_next_action_at", "next_action_at"),
        Index("ix_contacts_display_name_trgm", "display_name",
              postgresql_using="gin", postgresql_ops={"display_name": "gin_trgm_ops"}),
        Index("ix_contacts_stage_name_trgm", "stage_name",
              postgresql_using="gin", postgresql_ops={"stage_name": "gin_trgm_ops"}),
        Index("ix_contacts_notes_trgm", "notes",
              postgresql_using="gin", postgresql_ops={"notes": "gin_trgm_ops"}),
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ContactChannel(UuidPk, Timestamps, Base):
    __tablename__ = "contact_channels"
    __table_args__ = (
        Index(
            "uq_contact_channels_value",
            "channel_type",
            "normalized_value",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_contact_channels_primary",
            "contact_id",
            unique=True,
            postgresql_where=text("is_primary AND deleted_at IS NULL"),
        ),
        Index("ix_contact_channels_contact_id", "contact_id"),
        Index("ix_contact_channels_normalized_trgm", "normalized_value",
              postgresql_using="gin",
              postgresql_ops={"normalized_value": "gin_trgm_ops"}),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    channel_type: Mapped[ChannelType] = mapped_column(enum_column(ChannelType), nullable=False)
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    label: Mapped[str | None] = mapped_column(String(60))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contact: Mapped[Contact] = relationship(back_populates="channels")


class ContactStatus(Base):
    __tablename__ = "contact_statuses"
    __table_args__ = (
        Index("ix_contact_statuses_status_id", "status_id"),
        Index("ix_contact_statuses_group_id", "group_id", "contact_id"),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True
    )
    status_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("statuses.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("status_groups.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    note: Mapped[str | None] = mapped_column(Text)

    contact: Mapped[Contact] = relationship(back_populates="status_links")
    status: Mapped[Status] = relationship()


class ContactNote(UuidPk, Timestamps, Base):
    __tablename__ = "contact_notes"
    __table_args__ = (Index("ix_contact_notes_contact_id", "contact_id"),)

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_kind: Mapped[NoteAuthor] = mapped_column(
        enum_column(NoteAuthor), nullable=False, default=NoteAuthor.USER
    )

    contact: Mapped[Contact] = relationship(back_populates="note_entries")


class ContactReminder(UuidPk, Timestamps, Base):
    __tablename__ = "contact_reminders"
    __table_args__ = (
        Index("ix_contact_reminders_contact_id", "contact_id"),
        Index("ix_contact_reminders_due_at", "due_at"),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[ReminderState] = mapped_column(
        enum_column(ReminderState), nullable=False, default=ReminderState.PENDING
    )
    channel_type: Mapped[ChannelType | None] = mapped_column(enum_column(ChannelType))
    notes: Mapped[str | None] = mapped_column(Text)

    contact: Mapped[Contact] = relationship(back_populates="reminders")


class Interaction(UuidPk, Timestamps, Base):
    __tablename__ = "interactions"
    __table_args__ = (
        Index("ix_interactions_contact_id_occurred_at", "contact_id", "occurred_at"),
        Index(
            "uq_interactions_external",
            "channel_type",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    channel_type: Mapped[ChannelType] = mapped_column(enum_column(ChannelType), nullable=False)
    direction: Mapped[Direction] = mapped_column(enum_column(Direction), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    contact: Mapped[Contact] = relationship(back_populates="interactions")


class Exclusion(UuidPk, Timestamps, Base):
    __tablename__ = "exclusions"
    __table_args__ = (
        UniqueConstraint("kind", "normalized_value", name="uq_exclusions_kind_normalized_value"),
    )

    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)


class Deal(UuidPk, Timestamps, Base):
    __tablename__ = "deals"
    __table_args__ = (
        Index("ix_deals_contact_id", "contact_id"),
        Index("ix_deals_stage", "stage"),
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    stage: Mapped[DealStage] = mapped_column(
        enum_column(DealStage), nullable=False, default=DealStage.OPEN
    )
    source: Mapped[ContactSource | None] = mapped_column(enum_column(ContactSource))
    amount_expected: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contact: Mapped[Contact] = relationship(back_populates="deals")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Payment.paid_at",
    )


class Payment(UuidPk, Timestamps, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_deal_id", "deal_id"),
        Index("ix_payments_paid_at", "paid_at"),
    )

    deal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deals.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    method: Mapped[str | None] = mapped_column(String(60))
    external_ref: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    deal: Mapped[Deal] = relationship(back_populates="payments")


__all__ = [
    "StatusGroup",
    "Status",
    "Contact",
    "ContactChannel",
    "ContactStatus",
    "ContactNote",
    "ContactReminder",
    "Interaction",
    "Exclusion",
    "Deal",
    "Payment",
]
