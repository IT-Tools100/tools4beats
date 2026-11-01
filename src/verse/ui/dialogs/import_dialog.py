"""Диалог импорта CSV: маппинг колонок и предпросмотр."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from verse.services.transfer import FIELD_LABELS, Preview


class ImportDialog(QDialog):
    def __init__(self, preview: Preview, file_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preview = preview
        self.setWindowTitle("Импорт контактов")
        self.setMinimumSize(760, 620)

        layout = QVBoxLayout(self)

        header = QLabel(
            f"<b>{file_name}</b><br>"
            f"Колонок: {len(preview.headers)} · строк: {preview.total_rows}. "
            "Проверьте сопоставление полей — строки без имени будут пропущены."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        mapping_box = QGroupBox("Сопоставление колонок")
        form = QFormLayout(mapping_box)
        self._combos: dict[str, QComboBox] = {}
        for field_name, label in FIELD_LABELS.items():
            combo = QComboBox()
            combo.addItem("— не импортировать —", -1)
            for index, column in enumerate(preview.headers):
                combo.addItem(f"{index + 1}. {column}", index)
            if field_name in preview.mapping:
                position = combo.findData(preview.mapping[field_name])
                if position >= 0:
                    combo.setCurrentIndex(position)
            self._combos[field_name] = combo
            form.addRow(label, combo)
        layout.addWidget(mapping_box)

        table = QTableWidget(len(preview.rows), len(preview.headers))
        table.setHorizontalHeaderLabels(preview.headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        for row_index, row in enumerate(preview.rows):
            for column_index, value in enumerate(row):
                table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        layout.addWidget(QLabel("Предпросмотр (первые строки):"))
        layout.addWidget(table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Импортировать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self) -> None:
        if "display_name" not in self.mapping():
            QMessageBox.warning(self, "Импорт", "Выберите колонку с именем контакта.")
            return
        self.accept()

    def mapping(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for field_name, combo in self._combos.items():
            index = combo.currentData()
            if index is not None and index >= 0:
                result[field_name] = int(index)
        return result
