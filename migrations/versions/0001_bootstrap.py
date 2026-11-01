"""bootstrap: расширения PostgreSQL

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-11-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pg_trgm нужен для быстрого поиска по подстроке (ILIKE) и LIKE-индексов.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
