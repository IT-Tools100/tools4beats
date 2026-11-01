"""Фабрики тестовых данных."""

from __future__ import annotations

from verse.domain.dto import ChannelIn, ContactIn
from verse.domain.enums import ChannelType, ContactSource


def contact_in(
    name: str = "Test Artist",
    *,
    email: str | None = None,
    instagram: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
    source: ContactSource = ContactSource.MANUAL,
    do_not_contact: bool = False,
    status_ids: list | None = None,
) -> ContactIn:
    channels = []
    if email:
        channels.append(ChannelIn(channel_type=ChannelType.EMAIL, value=email))
    if instagram:
        channels.append(ChannelIn(channel_type=ChannelType.INSTAGRAM, value=instagram))
    if phone:
        channels.append(ChannelIn(channel_type=ChannelType.PHONE, value=phone))
    return ContactIn(
        display_name=name,
        notes=notes,
        source=source,
        do_not_contact=do_not_contact,
        channels=channels,
        status_ids=status_ids or [],
    )
