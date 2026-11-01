"""Dashboard: только реальные агрегаты из базы."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from verse.context import AppContext
from verse.domain.money import format_amounts
from verse.services import stats as stats_service
from verse.ui.bridge import AsyncRunner
from verse.ui.formatting import format_dt
from verse.ui.widgets.common import Card, make_button


class DashboardView(QWidget):
    def __init__(self, context: AppContext, runner: AsyncRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.runner = runner
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        refresh_button = make_button("Обновить")
        refresh_button.clicked.connect(self.refresh)
        header.addWidget(refresh_button)
        layout.addLayout(header)

        cards = QGridLayout()
        cards.setSpacing(10)
        self.card_total = Card("Всего контактов")
        self.card_active = Card("Активных")
        self.card_dnc = Card("Do Not Contact")
        self.card_trashed = Card("В корзине")
        self.card_deals = Card("Открытых сделок")
        self.card_revenue = Card("Фактический доход")
        self.card_potential = Card("Потенциальный доход")
        self.card_interactions = Card("Взаимодействий")
        widgets = [
            self.card_total,
            self.card_active,
            self.card_dnc,
            self.card_trashed,
            self.card_deals,
            self.card_revenue,
            self.card_potential,
            self.card_interactions,
        ]
        for index, widget in enumerate(widgets):
            cards.addWidget(widget, index // 4, index % 4)
        layout.addLayout(cards)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)

        status_box = QVBoxLayout()
        status_title = QLabel("Контакты по статусам")
        status_title.setObjectName("SectionTitle")
        status_box.addWidget(status_title)
        self.status_table = QTableWidget(0, 3)
        self.status_table.setHorizontalHeaderLabels(["Группа", "Статус", "Контактов"])
        self.status_table.horizontalHeader().setStretchLastSection(True)
        self.status_table.setColumnWidth(0, 175)
        self.status_table.setColumnWidth(1, 130)
        self.status_table.verticalHeader().setVisible(False)
        self.status_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        status_box.addWidget(self.status_table)
        bottom.addLayout(status_box, 1)

        upcoming_box = QVBoxLayout()
        upcoming_title = QLabel("Ближайшие действия")
        upcoming_title.setObjectName("SectionTitle")
        upcoming_box.addWidget(upcoming_title)
        self.upcoming_table = QTableWidget(0, 2)
        self.upcoming_table.setHorizontalHeaderLabels(["Когда", "Контакт"])
        self.upcoming_table.horizontalHeader().setStretchLastSection(True)
        self.upcoming_table.setColumnWidth(0, 140)
        self.upcoming_table.verticalHeader().setVisible(False)
        self.upcoming_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        upcoming_box.addWidget(self.upcoming_table)
        bottom.addLayout(upcoming_box, 1)

        layout.addLayout(bottom, 1)

    def refresh(self) -> None:
        self.runner.run(
            lambda: stats_service.dashboard(self.context.db), self._on_stats, self._on_error
        )

    def _on_stats(self, stats: stats_service.DashboardStats) -> None:
        self.card_total.set_value(str(stats.contacts_total))
        self.card_active.set_value(str(stats.contacts_active))
        self.card_dnc.set_value(str(stats.contacts_dnc))
        self.card_trashed.set_value(str(stats.contacts_trashed))
        self.card_deals.set_value(str(stats.deals_open))
        self.card_revenue.set_value(format_amounts(stats.revenue))
        self.card_potential.set_value(format_amounts(stats.potential))
        self.card_interactions.set_value(str(stats.interactions_total))

        self.status_table.setRowCount(len(stats.status_counts))
        for row, (group, status, count) in enumerate(stats.status_counts):
            self.status_table.setItem(row, 0, QTableWidgetItem(group))
            self.status_table.setItem(row, 1, QTableWidgetItem(status))
            self.status_table.setItem(row, 2, QTableWidgetItem(str(count)))

        self.upcoming_table.setRowCount(len(stats.upcoming))
        for row, (_contact_id, when, name) in enumerate(stats.upcoming):
            self.upcoming_table.setItem(row, 0, QTableWidgetItem(format_dt(when)))
            self.upcoming_table.setItem(row, 1, QTableWidgetItem(name))

    def _on_error(self, error: BaseException) -> None:
        self.card_total.set_value("—")
        self.card_revenue.set_value("нет связи с БД")
