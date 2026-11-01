"""Проверка состояния системы (БД, миграции, версии)."""

from __future__ import annotations

import platform
import sys

from sqlalchemy import text

from verse import __version__
from verse.db.session import Database


async def health(db: Database) -> dict[str, str | bool | None]:
    connected = await db.ping()
    server_version = await db.server_version() if connected else None
    revision: str | None = None
    if connected:
        try:
            async with db.engine.connect() as conn:
                revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:  # noqa: BLE001 — миграции могли не применяться
            revision = None

    from PySide6 import __version__ as qt_version

    return {
        "connected": connected,
        "server_version": server_version,
        "migration": revision,
        "app_version": __version__,
        "python_version": platform.python_version(),
        "qt_version": qt_version,
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "executable": sys.executable,
    }
