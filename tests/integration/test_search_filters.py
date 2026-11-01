"""Поиск, фильтры и сортировка CRM."""

from __future__ import annotations

from sqlalchemy import select

from tests.factories import contact_in
from verse.db.models import Status
from verse.domain.enums import ChannelType, ContactSource
from verse.domain.filters import ContactFilter


async def _status_id(db, slug: str):
    async with db.session() as session:
        return await session.scalar(select(Status.id).where(Status.slug == slug))


async def test_search_by_name_email_notes(contacts) -> None:
    await contacts.create(contact_in("Alpha Beats", email="alpha@studio.com", notes="нужен пак"))
    await contacts.create(contact_in("Beta Waves", instagram="@betawaves", notes="dark trap"))

    assert (await contacts.list(ContactFilter(query="alpha"))).total == 1
    assert (await contacts.list(ContactFilter(query="STUDIO.COM"))).total == 1
    assert (await contacts.list(ContactFilter(query="@betawaves"))).total == 1
    assert (await contacts.list(ContactFilter(query="dark trap"))).total == 1
    assert (await contacts.list(ContactFilter(query="нет такого"))).total == 0


async def test_filter_by_channel_and_source(contacts) -> None:
    await contacts.create(contact_in("With Email", email="one@mail.com"))
    await contacts.create(
        contact_in("From Spotify", source=ContactSource.SPOTIFY, instagram="@sp")
    )

    assert (await contacts.list(ContactFilter(has_email=True))).total == 1
    assert (await contacts.list(ContactFilter(has_phone=True))).total == 0
    assert (await contacts.list(ContactFilter(source=ContactSource.SPOTIFY))).total == 1
    assert (
        await contacts.list(ContactFilter(channel_type=ChannelType.EMAIL))
    ).total == 1


async def test_filter_by_status(contacts, db) -> None:
    new_id = await _status_id(db, "new")
    contacted_id = await _status_id(db, "contacted")
    await contacts.create(contact_in("Fresh", status_ids=[new_id]))
    await contacts.create(contact_in("Written", status_ids=[contacted_id]))
    await contacts.create(contact_in("No status"))

    assert (await contacts.list(ContactFilter(status_ids=[new_id]))).total == 1
    assert (await contacts.list(ContactFilter(status_ids=[new_id, contacted_id]))).total == 2


async def test_dnc_and_deleted_filters(contacts) -> None:
    await contacts.create(contact_in("Normal"))
    dnc_id = await contacts.create(contact_in("DoNotWrite", do_not_contact=True))
    trashed_id = await contacts.create(contact_in("Trashed"))
    await contacts.soft_delete(trashed_id)

    assert (await contacts.list(ContactFilter(only_dnc=True))).total == 1
    assert (await contacts.list(ContactFilter())).total == 2
    assert (await contacts.list(ContactFilter(only_deleted=True))).total == 1
    assert (await contacts.list(ContactFilter(include_deleted=True))).total == 3
    assert (await contacts.get(dnc_id)).do_not_contact is True


async def test_sorting_and_pagination(contacts) -> None:
    for name in ("Charlie", "Alpha", "Bravo"):
        await contacts.create(contact_in(name))

    page = await contacts.list(ContactFilter(), page=1, page_size=2, sort="name")
    assert [row.display_name for row in page.items] == ["Alpha", "Bravo"]
    assert page.total == 3
    assert page.pages == 2

    page2 = await contacts.list(ContactFilter(), page=2, page_size=2, sort="name")
    assert [row.display_name for row in page2.items] == ["Charlie"]

    desc = await contacts.list(ContactFilter(), sort="name", descending=True, page_size=1)
    assert desc.items[0].display_name == "Charlie"
