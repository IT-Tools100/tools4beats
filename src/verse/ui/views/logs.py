"""Журнал событий (audit_log)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from verse.context import AppContext
from verse.services import audit as audit_service
from verse.ui.bridge import AsyncRunner
from verse.ui.formatting import format_dt
from verse.ui.widgets.common import make_button

CATEGORIES = [
    ("Все категории", None),
    ("CRM", "crm"),
    ("Импорт", "import"),
    ("Экспорт", "export"),
    ("Задания", "job"),
    ("Интеграции", "integration"),
    ("Безопасность", "security"),
]
LEVELS = [("Все уровни", None), ("Info", "info"), ("Warning", "warning"), ("Error", "error")]


class LogsView(QWidget):
    def __init__(self, context: AppContext, runner: AsyncRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.runner = runner
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Журнал событий")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.category_combo = QComboBox()
        for label, value in CATEGORIES:
            self.category_combo.addItem(label, value)
        self.category_combo.currentIndexChanged.connect(self.refresh)

        self.level_combo = QComboBox()
        for label, value in LEVELS:
            self.level_combo.addItem(label, value)
        self.level_combo.currentIndexChanged.connect(self.refresh)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Фильтр по типу события")
        self.search_edit.returnPressed.connect(self.refresh)

        refresh_button = make_button("Обновить")
        refresh_button.clicked.connect(self.refresh)

        header.addWidget(self.search_edit)
        header.addWidget(self.category_combo)
        header.addWidget(self.level_combo)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        self.hint = QLabel("Секреты и токены в журнал не записываются.")
        self.hint.setObjectName("Hint")
        layout.addWidget(self.hint)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Время", "Уровень", "Категория", "Событие", "Результат", "Сообщение"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 190)
        self.table.setColumnWidth(4, 100)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        category = self.category_combo.currentData()
        level = self.level_combo.currentData()
        search = self.search_edit.text().strip() or None

        async def load():
            async with self.context.db.session() as session:
                return await audit_service.list_entries(
                    session, limit=300, category=category, level=level, search=search
                )

        self.runner.run(load, self._on_entries, self._on_error)

    def _on_entries(self, entries) -> None:
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                format_dt(entry.occurred_at),
                entry.level,
                entry.category,
                entry.event_type,
                entry.result or "",
                entry.message or "",
            ]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))

    def _on_error(self, error: BaseException) -> None:
        self.hint.setText(
            getattr(error, "user_message", None) or f"Не удалось загрузить журнал: {error}"
        )
