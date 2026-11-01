"""Roadmap: честный список модулей и их состояния.

Единственное место, где перечислены нереализованные разделы: они не появляются
в навигации, пока не начнут работать (SPEC §1, §23).
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

MODULES: list[tuple[str, str, str]] = [
    ("Dashboard (реальные агрегаты)", "Реализовано", "Этап 0–1"),
    ("CRM: контакты, каналы, статусы, заметки", "Реализовано", "Этап 1"),
    ("CRM: сделки и платежи", "Реализовано", "Этап 1"),
    ("Поиск, фильтры, сортировка, массовые действия", "Реализовано", "Этап 1"),
    ("Импорт и экспорт CSV", "Реализовано", "Этап 1"),
    ("Корзина, восстановление, Do Not Contact", "Реализовано", "Этап 1"),
    ("Журнал событий и настройки", "Реализовано", "Этап 0"),
    ("Artist Library и Spotify Discovery", "Запланировано", "Этап 2"),
    ("Instagram Discovery (импорт-центричный)", "Запланировано", "Этап 2"),
    ("Кампании, шаблоны, follow-up", "Запланировано", "Этап 3"),
    ("Email-канал (SMTP/IMAP)", "Запланировано", "Этап 3"),
    ("iMessage, WhatsApp, Discord, Instagram-ответы", "Запланировано (спайки)", "Этап 4"),
    ("Автоматизации, планировщик, Beat Series", "Запланировано", "Этап 5"),
    ("AI-ассистент (DeepSeek, скриншоты)", "Запланировано", "Этап 6"),
    ("Каталог битов и размещения", "Запланировано", "Этап 7"),
    ("Telegram-бот и резервное копирование", "Запланировано", "Этап 8"),
    ("Статистика и отчёты", "Запланировано", "Этап 5+"),
]


class RoadmapView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Roadmap")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        hint = QLabel(
            "Разделы появляются в навигации только после того, как начинают работать. "
            "Ниже — статус каждого модуля по PROJECT_PLAN.md."
        )
        hint.setWordWrap(True)
        hint.setObjectName("Hint")
        layout.addWidget(hint)

        self.table = QTableWidget(len(MODULES), 3)
        self.table.setHorizontalHeaderLabels(["Модуль", "Состояние", "План"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 460)
        self.table.setColumnWidth(1, 210)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        for row, (name, state, stage) in enumerate(MODULES):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            state_item = QTableWidgetItem(state)
            state_item.setForeground(
                QColor("#34C759") if state == "Реализовано" else QColor("#8E8E93")
            )
            self.table.setItem(row, 1, state_item)
            self.table.setItem(row, 2, QTableWidgetItem(stage))
        layout.addWidget(self.table, 1)
