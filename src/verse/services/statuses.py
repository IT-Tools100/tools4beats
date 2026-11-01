"""Статусы и группы статусов."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from verse.db.models import Status, StatusGroup
from verse.domain.dto import StatusGroupView, StatusOption


async def list_groups(session: AsyncSession) -> list[StatusGroupView]:
    stmt = (
        select(StatusGroup)
        .options(selectinload(StatusGroup.statuses))
        .order_by(StatusGroup.sort_order, StatusGroup.name)
    )
    result = await session.execute(stmt)
    groups: list[StatusGroupView] = []
    for group in result.scalars().unique():
        groups.append(
            StatusGroupView(
                id=group.id,
                name=group.name,
                slug=group.slug,
                color=group.color,
                allows_multiple=group.allows_multiple,
                statuses=[
                    StatusOption(
                        id=status.id,
                        name=status.name,
                        color=status.color,
                        group_name=group.name,
                        group_slug=group.slug,
                        allows_multiple=group.allows_multiple,
                    )
                    for status in sorted(group.statuses, key=lambda s: (s.sort_order, s.name))
                ],
            )
        )
    return groups


async def fetch_by_ids(session: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, Status]:
    if not ids:
        return {}
    stmt = (
        select(Status)
        .where(Status.id.in_(ids))
        .options(selectinload(Status.group))
    )
    result = await session.execute(stmt)
    return {status.id: status for status in result.scalars().unique()}
