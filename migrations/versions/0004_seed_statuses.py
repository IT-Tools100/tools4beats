"""seed: стартовые группы и статусы CRM

Идемпотентно: фиксированные UUID + ON CONFLICT DO NOTHING.
Пользовательские статусы миграция не трогает.

Revision ID: 0004_seed_statuses
Revises: 0003_enum_checks
Create Date: 2026-11-01
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_seed_statuses"
down_revision: str | None = "0003_enum_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNNEL_GROUP = uuid.UUID("11111111-1111-4111-8111-111111111101")
INTEREST_GROUP = uuid.UUID("11111111-1111-4111-8111-111111111102")

GROUPS = [
    (FUNNEL_GROUP, "Воронка", "funnel", "#3b82f6", False, 0),
    (INTEREST_GROUP, "Заинтересованность", "interest", "#f59e0b", True, 1),
]

STATUSES = [
    # (group, name, slug, color, order, terminal)
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


def _status_id(index: int) -> uuid.UUID:
    return uuid.UUID(f"22222222-2222-4222-8222-2222222222{index:02d}")


def upgrade() -> None:
    groups = sa.table(
        "status_groups",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("color", sa.String()),
        sa.column("allows_multiple", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        groups,
        [
            {
                "id": group_id,
                "name": name,
                "slug": slug,
                "color": color,
                "allows_multiple": allows_multiple,
                "sort_order": order,
                "is_system": True,
            }
            for group_id, name, slug, color, allows_multiple, order in GROUPS
        ],
    )

    statuses = sa.table(
        "statuses",
        sa.column("id", sa.Uuid()),
        sa.column("group_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("color", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_terminal", sa.Boolean()),
        sa.column("is_default", sa.Boolean()),
    )
    rows = []
    for index, (group_id, name, slug, color, order, terminal) in enumerate(STATUSES, start=1):
        rows.append(
            {
                "id": _status_id(index),
                "group_id": group_id,
                "name": name,
                "slug": slug,
                "color": color,
                "sort_order": order,
                "is_terminal": terminal,
                "is_default": index == 1,
            }
        )
    op.bulk_insert(statuses, rows)


def downgrade() -> None:
    status_ids = ", ".join(f"'{_status_id(i)}'" for i in range(1, len(STATUSES) + 1))
    op.execute(f"DELETE FROM statuses WHERE id IN ({status_ids})")
    group_ids = ", ".join(f"'{group_id}'" for group_id, *_ in GROUPS)
    op.execute(f"DELETE FROM status_groups WHERE id IN ({group_ids})")
