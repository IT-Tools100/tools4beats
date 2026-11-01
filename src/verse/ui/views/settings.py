"""Настройки: параметры подключения, состояние системы, папка данных."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from verse.context import AppContext
from verse.services import system as system_service
from verse.ui.bridge import AsyncRunner
from verse.ui.formatting import mask_dsn
from verse.ui.widgets.common import make_button


class SettingsView(QWidget):
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
        title = QLabel("Настройки")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)
        check_button = make_button("Проверить подключение")
        check_button.clicked.connect(self.refresh)
        open_button = make_button("Открыть папку данных")
        open_button.clicked.connect(self._open_data_dir)
        header.addWidget(check_button)
        header.addWidget(open_button)
        layout.addLayout(header)

        db_box = QGroupBox("База данных")
        db_form = QFormLayout(db_box)
        self.dsn_edit = QLineEdit(mask_dsn(self.context.settings.database_url))
        self.dsn_edit.setReadOnly(True)
        self.status_value = QLabel("—")
        self.server_value = QLabel("—")
        self.migration_value = QLabel("—")
        db_form.addRow("Подключение", self.dsn_edit)
        db_form.addRow("Состояние", self.status_value)
        db_form.addRow("Версия PostgreSQL", self.server_value)
        db_form.addRow("Миграция", self.migration_value)
        layout.addWidget(db_box)

        app_box = QGroupBox("Приложение")
        app_form = QFormLayout(app_box)
        self.app_value = QLabel("—")
        self.python_value = QLabel("—")
        self.qt_value = QLabel("—")
        self.platform_value = QLabel("—")
        self.data_value = QLabel(str(self.context.settings.data_dir))
        self.data_value.setTextInteractionFlags(self.data_value.textInteractionFlags())
        app_form.addRow("Версия", self.app_value)
        app_form.addRow("Python", self.python_value)
        app_form.addRow("Qt", self.qt_value)
        app_form.addRow("Платформа", self.platform_value)
        app_form.addRow("Данные", self.data_value)
        layout.addWidget(app_box)

        hint = QLabel(
            "Секреты (токены, пароли) хранятся только в macOS Keychain и в этом окне не отображаются."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

    def refresh(self) -> None:
        self.runner.run(
            lambda: system_service.health(self.context.db), self._on_health, self._on_error
        )

    def _on_health(self, info: dict) -> None:
        connected = bool(info.get("connected"))
        self.status_value.setText("подключено" if connected else "нет подключения")
        self.status_value.setStyleSheet(
            "color: #15803d;" if connected else "color: #b91c1c;"
        )
        self.server_value.setText(str(info.get("server_version") or "—"))
        self.migration_value.setText(str(info.get("migration") or "не применялись"))
        self.app_value.setText(str(info.get("app_version")))
        self.python_value.setText(str(info.get("python_version")))
        self.qt_value.setText(str(info.get("qt_version")))
        self.platform_value.setText(str(info.get("platform")))

    def _on_error(self, error: BaseException) -> None:
        self.status_value.setText("ошибка проверки")
        self.status_value.setStyleSheet("color: #b91c1c;")

    def _open_data_dir(self) -> None:
        path = self.context.settings.data_dir
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
