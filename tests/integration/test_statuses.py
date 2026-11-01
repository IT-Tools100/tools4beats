"""Статусы: группы, взаимоисключение, мультивыбор."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from tests.factories import contact_in
from verse.db.models import Status
from verse.errors import ValidationError
from verse.services import statuses as status_service


async def _status_ids(db, slugs: list[str]) -> list:
    async with db.session() as session:
        result = await session.execute(select(Status).where(Status.slug.in_(slugs)))
        return [status.id for status in result.scalars()]


async def test_seed_groups_present(db) -> None:
    async with db.session() as session:
        groups = await status_service.list_groups(session)
    names = {group.name for group in groups}
    assert {"Воронка", "Заинтересованность"} <= names
    funnel = next(group for group in groups if group.slug == "funnel")
    interest = next(group for group in groups if group.slug == "interest")
    assert funnel.allows_multiple is False
    assert interest.allows_multiple is True
    assert len(funnel.statuses) == 8
    assert len(interest.statuses) == 3


async def test_single_status_per_funnel(contacts, db) -> None:
    new_id, contacted_id = await _status_ids(db, ["new", "contacted"])
    contact_id = await contacts.create(contact_in("Status Test", status_ids=[new_id]))

    detail = await contacts.get(contact_id)
    assert [status.name for status in detail.statuses] == ["New"]

    await contacts.update(
        contact_id, contact_in("Status Test", status_ids=[contacted_id])
    )
    detail = await contacts.get(contact_id)
    assert [status.name for status in detail.statuses] == ["Contacted"]


async def test_two_funnel_statuses_rejected(contacts, db) -> None:
    new_id, contacted_id = await _status_ids(db, ["new", "contacted"])
    with pytest.raises(ValidationError):
        await contacts.create(
            contact_in("Bad", status_ids=[new_id, contacted_id])
        )


async def test_multiple_interest_statuses_allowed(contacts, db) -> None:
    cold_id, warm_id = await _status_ids(db, ["cold", "warm"])
    contact_id = await contacts.create(contact_in("Multi", status_ids=[cold_id, warm_id]))
    detail = await contacts.get(contact_id)
    assert {status.name for status in detail.statuses} == {"Cold", "Warm"}
