"""Дымовые тесты интерфейса: окно собирается, навигация работает, данные грузятся."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine, text

from verse.context import AppContext
from verse.domain.dto import ChannelIn, ContactIn
from verse.domain.enums import ChannelType
from verse.runtime import Runtime
from verse.ui.main_window import MainWindow

pytestmark = pytest.mark.usefixtures("migrated_database")

DATA_TABLES = (
    "audit_log, data_transfers, payments, deals, interactions, contact_reminders, "
    "contact_notes, contact_statuses, contact_channels, contacts"
)


def _truncate(url: str) -> None:
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f"TRUNCATE {DATA_TABLES} RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest.fixture
def runtime():
    rt = Runtime()
    rt.start()
    yield rt
    rt.stop()


@pytest.fixture
def context(test_url: str, settings, runtime):
    _truncate(test_url)
    ctx = AppContext.build(settings)
    yield ctx
    try:
        runtime.run_blocking(ctx.db.disposed)
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture
def window(qtbot, runtime, context):
    ui = MainWindow(context, runtime)
    qtbot.addWidget(ui)
    ui.show()
    yield ui
    ui.runner.close()
    ui.close()
    qtbot.wait(50)


def test_navigation_is_honest(window) -> None:
    labels = [window.nav.item(index).text() for index in range(window.nav.count())]
    assert labels == ["Dashboard", "CRM", "Журнал", "Настройки", "Roadmap"]


def test_database_status_reported(window, qtbot) -> None:
    qtbot.waitUntil(
        lambda: window.statusBar().currentMessage()
        != "Проверка подключения к PostgreSQL…",
        timeout=15_000,
    )
    message = window.statusBar().currentMessage()
    assert "подключено" in message, f"status={message!r}"


def test_contact_appears_in_table(window, qtbot, runtime) -> None:
    async def seed():
        return await window.context.contacts.create(
            ContactIn(
                display_name="UI Test Artist",
                channels=[ChannelIn(channel_type=ChannelType.EMAIL, value="ui@test.com")],
            )
        )

    runtime.run_blocking(seed, timeout=15)

    window.navigate(1)
    qtbot.waitUntil(lambda: window.crm.model.rowCount() == 1, timeout=10_000)
    index = window.crm.model.index(0, 0)
    assert window.crm.model.data(index) == "UI Test Artist"
    qtbot.waitUntil(lambda: window.crm.total == 1, timeout=5_000)


def test_app_has_single_qapplication(qtbot) -> None:
    assert QApplication.instance() is not None


def test_database_engine_is_reachable(context, runtime) -> None:
    assert runtime.run_blocking(lambda: context.db.ping()) is True
