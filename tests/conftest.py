"""Общие фикстуры тестов.

Схема тестовой БД строится через Alembic (а не `create_all`), чтобы тесты
проверяли именно миграции.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from verse.config import Settings
from verse.db.session import Database
from verse.services.contacts import ContactService
from verse.services.deals import DealService

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TEST_URL = "postgresql+psycopg://verse:verse@127.0.0.1:5433/verse_test"

DATA_TABLES = (
    "audit_log",
    "data_transfers",
    "payments",
    "deals",
    "interactions",
    "contact_reminders",
    "contact_notes",
    "contact_statuses",
    "contact_channels",
    "contacts",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: требует запущенного PostgreSQL")


def test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_URL)


def alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def test_url() -> str:
    return test_database_url()


@pytest.fixture(scope="session", autouse=True)
def migrated_database(test_url: str) -> None:
    config = alembic_config(test_url)
    command.upgrade(config, "head")
    yield


@pytest.fixture
def settings(test_url: str, tmp_path: Path) -> Settings:
    return Settings(
        database_url=test_url,
        test_database_url=test_url,
        data_dir=tmp_path / "data",
        log_level="WARNING",
    )


@pytest.fixture
async def db(test_url: str, migrated_database) -> Database:
    database = Database(test_url, pool_size=2)
    async with database.engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE {', '.join(DATA_TABLES)} RESTART IDENTITY CASCADE")
        )
    yield database
    await database.disposed()


@pytest.fixture
def contacts(db: Database) -> ContactService:
    return ContactService(db)


@pytest.fixture
def deals(db: Database) -> DealService:
    return DealService(db)
