"""Подключение к PostgreSQL и единица работы (unit of work)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

log = logging.getLogger(__name__)


class Database:
    def __init__(self, url: str, *, echo: bool = False, pool_size: int = 5) -> None:
        self.url = url
        self.engine: AsyncEngine = create_async_engine(
            url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=5,
            pool_pre_ping=True,
            connect_args={"application_name": "project-verse"},
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False, autoflush=False
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:  # noqa: BLE001 - диагностика подключения
            log.warning("database ping failed: %s", exc)
            return False

    async def server_version(self) -> str | None:
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SHOW server_version"))
                return str(result.scalar_one())
        except Exception:  # noqa: BLE001
            return None

    async def disposed(self) -> None:
        await self.engine.dispose()


@asynccontextmanager
async def transaction(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Одна команда — одна транзакция. Коммит при успехе, откат при ошибке."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
