"""Фильтры списков (не зависят от UI и ORM)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from verse.domain.enums import ChannelType, ContactSource


@dataclass(slots=True)
class ContactFilter:
    query: str | None = None
    status_ids: list[uuid.UUID] = field(default_factory=list)
    channel_type: ChannelType | None = None
    source: ContactSource | None = None
    has_email: bool | None = None
    has_phone: bool | None = None
    only_dnc: bool = False
    include_deleted: bool = False
    only_deleted: bool = False


SORT_FIELDS = {
    "name": "display_name",
    "last_contact": "last_contact_at",
    "next_action": "next_action_at",
    "created": "created_at",
}
