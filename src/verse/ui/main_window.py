"""Главное окно: сайдбар, страницы, статус подключения к БД."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from verse.context import AppContext
from verse.runtime import Runtime
from verse.services import system as system_service
from verse.ui.bridge import AsyncRunner
from verse.ui.views.crm import CRMView
from verse.ui.views.dashboard import DashboardView
from verse.ui.views.logs import LogsView
from verse.ui.views.roadmap import RoadmapView
from verse.ui.views.settings import SettingsView

NAV_ITEMS = ["Dashboard", "CRM", "Журнал", "Настройки", "Roadmap"]


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext, runtime: Runtime) -> None:
        super().__init__()
        self.context = context
        self.runtime = runtime
        self.runner = AsyncRunner(runtime, self)
        self.setWindowTitle("Project Verse")
        self.resize(1280, 820)
        self._build_ui()
        self.check_health()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Content")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(184)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 18, 0, 12)
        sidebar_layout.setSpacing(8)

        brand = QLabel("Project Verse")
        brand.setObjectName("Brand")
        brand.setContentsMargins(20, 0, 0, 10)
        sidebar_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setObjectName("SidebarNav")
        for name in NAV_ITEMS:
            self.nav.addItem(QListWidgetItem(name))
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self.nav, 1)

        version = QLabel("0.1.0 · Этап 1")
        version.setObjectName("SidebarVersion")
        version.setContentsMargins(20, 0, 0, 4)
        sidebar_layout.addWidget(version)

        layout.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.dashboard = DashboardView(self.context, self.runner, self)
        self.crm = CRMView(self.context, self.runner, self)
        self.logs = LogsView(self.context, self.runner, self)
        self.settings = SettingsView(self.context, self.runner, self)
        self.roadmap = RoadmapView(self)
        for view in (self.dashboard, self.crm, self.logs, self.settings, self.roadmap):
            self.stack.addWidget(view)
        layout.addWidget(self.stack, 1)

        self.setCentralWidget(root)
        self.statusBar().showMessage("Проверка подключения к PostgreSQL…")

    # --- навигация --------------------------------------------------------
    def _on_nav_changed(self, index: int) -> None:
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        current = self.stack.currentWidget()
        refresh = getattr(current, "refresh", None)
        if callable(refresh):
            refresh()
        elif index == 4:
            pass

    def navigate(self, index: int) -> None:
        """Для тестов и горячих клавиш."""
        self.nav.setCurrentRow(index)

    # --- состояние --------------------------------------------------------
    def check_health(self) -> None:
        self.runner.run(
            lambda: system_service.health(self.context.db),
            self._on_health,
            self._on_health_error,
        )

    def _on_health(self, info: dict) -> None:
        if info.get("connected"):
            text = (
                f"PostgreSQL: подключено · {info.get('server_version')} · "
                f"миграция {info.get('migration') or '—'} · "
                f"{info.get('platform')}"
            )
        else:
            text = (
                "PostgreSQL: нет подключения. Запустите базу командой `make db-up` "
                "и повторите проверку."
            )
        self.statusBar().showMessage(str(text))

    def _on_health_error(self, error: BaseException) -> None:
        self.statusBar().showMessage(f"PostgreSQL: ошибка подключения — {error}")

    def closeEvent(self, event) -> None:  # noqa: N802
        self.runner.close()
        super().closeEvent(event)
