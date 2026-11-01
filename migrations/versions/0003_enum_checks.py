"""enum checks: проверки допустимых значений перечислений

Alembic не генерирует CHECK-ограничения для Enum(native_enum=False)
автоматически, поэтому добавляем их явно. Это страховка на уровне БД:
приложение валидирует значения через Pydantic и SQLAlchemy, но прямой SQL
тоже не сможет записать мусор.

Revision ID: 0003_enum_checks
Revises: 0002_crm_core
Create Date: 2026-11-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_enum_checks"
down_revision: str | None = "0002_crm_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECKS: dict[str, dict[str, tuple[str, ...]]] = {
    "contacts": {
        "source": ("manual", "instagram", "spotify", "import", "referral", "campaign", "other"),
    },
    "contact_channels": {
        "channel_type": (
            "instagram", "spotify", "youtube", "soundcloud", "discord", "phone",
            "whatsapp", "imessage", "email", "telegram", "other",
        ),
    },
    "contact_notes": {"author_kind": ("user", "ai", "system")},
    "contact_reminders": {
        "state": ("pending", "done", "cancelled", "missed"),
        "channel_type": (
            "instagram", "spotify", "youtube", "soundcloud", "discord", "phone",
            "whatsapp", "imessage", "email", "telegram", "other",
        ),
    },
    "interactions": {
        "channel_type": (
            "instagram", "spotify", "youtube", "soundcloud", "discord", "phone",
            "whatsapp", "imessage", "email", "telegram", "other",
        ),
        "direction": ("in", "out"),
    },
    "deals": {
        "stage": ("open", "won", "lost"),
        "source": ("manual", "instagram", "spotify", "import", "referral", "campaign", "other"),
    },
    "audit_log": {
        "level": ("debug", "info", "warning", "error"),
        "result": ("started", "succeeded", "failed", "cancelled", "missed"),
    },
    "data_transfers": {
        "direction": ("import", "export"),
        "format": ("csv", "xlsx", "txt"),
        "state": ("running", "completed", "failed"),
    },
}


def upgrade() -> None:
    for table, columns in _CHECKS.items():
        for column, values in columns.items():
            allowed = ", ".join(f"'{value}'" for value in values)
            op.create_check_constraint(
                f"ck_{table}_{column}_values",
                table,
                f"{column} IN ({allowed})",
            )


def downgrade() -> None:
    for table, columns in _CHECKS.items():
        for column in columns:
            op.drop_constraint(f"ck_{table}_{column}_values", table, type_="check")
