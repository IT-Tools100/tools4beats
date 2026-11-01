"""Проверка миграций: накат, откат, повторный накат, отсутствие расхождений."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from tests.conftest import alembic_config

MIGRATION_DB = "verse_migration_test"


def _admin_engine(test_url: str):
    admin_url = test_url.rsplit("/", 1)[0] + "/postgres"
    return create_engine(admin_url, isolation_level="AUTOCOMMIT")


def _migration_url(test_url: str) -> str:
    return test_url.rsplit("/", 1)[0] + "/" + MIGRATION_DB


def test_migrations_upgrade_downgrade(test_url: str) -> None:
    from alembic import command

    engine = _admin_engine(test_url)
    with engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{MIGRATION_DB}"'))
        connection.execute(text(f'CREATE DATABASE "{MIGRATION_DB}"'))

    url = _migration_url(test_url)
    config = alembic_config(url)
    try:
        command.upgrade(config, "head")

        target = create_engine(url)
        with target.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            statuses = connection.scalar(text("SELECT count(*) FROM statuses"))
            groups = connection.scalar(text("SELECT count(*) FROM status_groups"))
            tables = connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
        target.dispose()

        assert revision == "0004_seed_statuses"
        assert statuses == 11
        assert groups == 2
        assert tables >= 14

        # Полный откат должен проходить без ошибок (нет разрушающих данных).
        command.downgrade(config, "base")
        command.upgrade(config, "head")

        # Схема после наката должна совпадать с моделями.
        command.check(config)
    finally:
        with engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{MIGRATION_DB}"'))
        engine.dispose()
