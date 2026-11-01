"""CRM: создание, чтение, изменение, удаление контакта."""

from __future__ import annotations

import pytest

from tests.factories import contact_in
from verse.domain.dto import ChannelIn, ContactIn
from verse.domain.enums import ChannelType, ContactSource
from verse.domain.filters import ContactFilter
from verse.errors import DuplicateChannelError, NotFoundError, ValidationError


async def test_create_and_read(contacts) -> None:
    contact_id = await contacts.create(
        contact_in("Night Rider", email="NR@Example.com", instagram="@nightrider")
    )
    detail = await contacts.get(contact_id)

    assert detail.display_name == "Night Rider"
    assert len(detail.channels) == 2
    assert {c.normalized_value for c in detail.channels} == {"nr@example.com", "nightrider"}
    assert sum(1 for c in detail.channels if c.is_primary) == 1


async def test_update_replaces_channels(contacts) -> None:
    contact_id = await contacts.create(contact_in("Old Name", email="old@example.com"))

    await contacts.update(
        contact_id,
        ContactIn(
            display_name="New Name",
            source=ContactSource.REFERRAL,
            notes="обновлено",
            channels=[ChannelIn(channel_type=ChannelType.INSTAGRAM, value="@newhandle")],
        ),
    )
    detail = await contacts.get(contact_id)

    assert detail.display_name == "New Name"
    assert detail.source is ContactSource.REFERRAL
    assert [c.channel_type for c in detail.channels] == [ChannelType.INSTAGRAM]
    # старый email освобождён и может быть привязан к другому контакту
    second = await contacts.create(contact_in("Other", email="old@example.com"))
    assert (await contacts.get(second)).display_name == "Other"


async def test_duplicate_channel_rejected(contacts) -> None:
    await contacts.create(contact_in("First", email="dup@example.com"))
    with pytest.raises(DuplicateChannelError):
        await contacts.create(contact_in("Second", email="DUP@example.com"))


async def test_empty_name_rejected(contacts) -> None:
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError):
        ContactIn(display_name="   ")
    # Сервис дополнительно проверяет имя (защита от вызова в обход DTO).
    with pytest.raises(ValidationError):
        await contacts.create(ContactIn.model_construct(display_name="  ", channels=[]))


async def test_trash_restore_purge(contacts) -> None:
    contact_id = await contacts.create(contact_in("Temp"))

    await contacts.soft_delete(contact_id)
    assert (await contacts.list(ContactFilter())).total == 0
    assert (await contacts.list(ContactFilter(only_deleted=True))).total == 1

    await contacts.restore(contact_id)
    assert (await contacts.list(ContactFilter())).total == 1

    await contacts.purge(contact_id)
    assert (await contacts.list(ContactFilter(include_deleted=True))).total == 0
    with pytest.raises(NotFoundError):
        await contacts.get(contact_id)


async def test_bulk_operations(contacts) -> None:
    ids = [await contacts.create(contact_in(f"Artist {i}")) for i in range(3)]

    assert await contacts.bulk_trash(ids[:2]) == 2
    assert (await contacts.list(ContactFilter(only_deleted=True))).total == 2

    assert await contacts.set_dnc(ids[2:], True, "просил не писать") == 1
    page = await contacts.list(ContactFilter(only_dnc=True))
    assert page.total == 1
    assert page.items[0].do_not_contact is True

    assert await contacts.bulk_purge(ids) == 3


async def test_note_history(contacts) -> None:
    contact_id = await contacts.create(contact_in("Note Keeper"))

    await contacts.add_note(contact_id, "  отправил 3 бита  ")
    await contacts.add_note(contact_id, "ответил через день")

    detail = await contacts.get(contact_id)
    assert [note.body for note in detail.notes_history] == [
        "ответил через день",
        "отправил 3 бита",
    ]
    assert detail.notes_history[0].author_kind == "user"

    with pytest.raises(ValidationError):
        await contacts.add_note(contact_id, "   ")
