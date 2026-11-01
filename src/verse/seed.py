"""Идемпотентное заполнение справочников (`make seed`).

Миграция 0004 уже создаёт статусы; команда полезна, если справочники были
удалены вручную или база создана без миграций.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from verse.config import load_settings
from verse.db.session import Database

FUNNEL_GROUP = "11111111-1111-4111-8111-111111111101"
INTEREST_GROUP = "11111111-1111-4111-8111-111111111102"

GROUPS = [
    (FUNNEL_GROUP, "Воронка", "funnel", "#3b82f6", False, 0),
    (INTEREST_GROUP, "Заинтересованность", "interest", "#f59e0b", True, 1),
]

STATUSES = [
    (FUNNEL_GROUP, "New", "new", "#6b7280", 0, False),
    (FUNNEL_GROUP, "Contacted", "contacted", "#0ea5e9", 1, False),
    (FUNNEL_GROUP, "Replied", "replied", "#22c55e", 2, False),
    (FUNNEL_GROUP, "Interested", "interested", "#84cc16", 3, False),
    (FUNNEL_GROUP, "Sent Beats", "sent_beats", "#eab308", 4, False),
    (FUNNEL_GROUP, "Negotiation", "negotiation", "#f97316", 5, False),
    (FUNNEL_GROUP, "Client", "client", "#16a34a", 6, True),
    (FUNNEL_GROUP, "Rejected", "rejected", "#ef4444", 7, True),
    (INTEREST_GROUP, "Cold", "cold", "#60a5fa", 0, False),
    (INTEREST_GROUP, "Warm", "warm", "#f59e0b", 1, False),
    (INTEREST_GROUP, "Hot", "hot", "#dc2626", 2, False),
]


async def ensure_seed(db: Database) -> int:
    inserted = 0
    async with db.session() as session:
        for group_id, name, slug, color, allows_multiple, order in GROUPS:
            result = await session.execute(
                text(
                    """
                    INSERT INTO status_groups (id, name, slug, color, allows_multiple,
                                               sort_order, is_system)
                    VALUES (:id, :name, :slug, :color, :allows_multiple, :sort_order, true)
                    ON CONFLICT (slug) DO NOTHING
                    """
                ),
                {
                    "id": group_id,
                    "name": name,
                    "slug": slug,
                    "color": color,
                    "allows_multiple": allows_multiple,
                    "sort_order": order,
                },
            )
            inserted += result.rowcount or 0

        for index, (group_id, name, slug, color, order, terminal) in enumerate(STATUSES, start=1):
            status_id = f"22222222-2222-4222-8222-2222222222{index:02d}"
            result = await session.execute(
                text(
                    """
                    INSERT INTO statuses (id, group_id, name, slug, color, sort_order,
                                          is_terminal, is_default)
                    VALUES (:id, :group_id, :name, :slug, :color, :sort_order,
                            :is_terminal, :is_default)
                    ON CONFLICT (group_id, slug) DO NOTHING
                    """
                ),
                {
                    "id": status_id,
                    "group_id": group_id,
                    "name": name,
                    "slug": slug,
                    "color": color,
                    "sort_order": order,
                    "is_terminal": terminal,
                    "is_default": index == 1,
                },
            )
            inserted += result.rowcount or 0
        await session.commit()
    return inserted


def main() -> int:
    settings = load_settings()
    db = Database(settings.database_url)

    async def run() -> int:
        try:
            return await ensure_seed(db)
        finally:
            await db.disposed()

    count = asyncio.run(run())
    print(f"Справочники в порядке. Добавлено записей: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
