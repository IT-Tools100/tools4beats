"""Экран CRM: таблица контактов, поиск, фильтры, массовые действия."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from verse.context import AppContext
from verse.domain.dto import ContactDetail, ContactRow, Page
from verse.domain.enums import SOURCE_LABELS, ChannelType, ContactSource
from verse.domain.filters import ContactFilter
from verse.domain.money import format_amounts
from verse.services import transfer as transfer_service
from verse.ui.bridge import AsyncRunner
from verse.ui.dialogs.contact_dialog import ContactDialog
from verse.ui.dialogs.import_dialog import ImportDialog
from verse.ui.formatting import format_dt, plural_ru
from verse.ui.widgets.common import Banner, make_button

PAGE_SIZE = 50


class ContactTableModel(QAbstractTableModel):
    COLUMNS = [
        ("Контакт", "name"),
        ("Каналы", "channels"),
        ("Статусы", "statuses"),
        ("Был контакт", "last"),
        ("Действие", "next"),
        ("Доход", "revenue"),
        ("Потенциал", "potential"),
        ("Заметки", "notes"),
    ]
    SORT_KEYS = {"Контакт": "name", "Был контакт": "last_contact", "Действие": "next_action"}

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[ContactRow] = []

    def set_rows(self, rows: list[ContactRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_at(self, index: int) -> ContactRow | None:
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section][0]
        return section + 1

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._text(row, column)
        if role == Qt.ItemDataRole.ForegroundRole:
            if row.do_not_contact:
                return QColor("#b91c1c")
            if row.is_deleted:
                return QColor("#9ca3af")
        if role == Qt.ItemDataRole.ToolTipRole:
            if column == 1:
                return "\n".join(
                    f"{channel.channel_type.label}: {channel.normalized_value}"
                    for channel in row.channels
                )
            if column == 2:
                return "\n".join(f"{s.group_name}: {s.name}" for s in row.statuses)
            if column == 7 and row.notes:
                return row.notes
        return None

    def _text(self, row: ContactRow, column: int) -> str:
        if column == 0:
            return row.display_name
        if column == 1:
            if not row.channels:
                return "—"
            parts = []
            for channel in row.channels[:3]:
                parts.append(f"{channel.channel_type.label}: {channel.normalized_value}")
            if len(row.channels) > 3:
                parts.append(f"+{len(row.channels) - 3}")
            return " · ".join(parts)
        if column == 2:
            return " · ".join(status.name for status in row.statuses) or "—"
        if column == 3:
            return format_dt(row.last_contact_at)
        if column == 4:
            return format_dt(row.next_action_at)
        if column == 5:
            return format_amounts(row.revenue)
        if column == 6:
            return format_amounts(row.potential)
        if column == 7:
            notes = (row.notes or "").replace("\n", " ").strip()
            return notes[:80] + ("…" if len(notes) > 80 else "")
        return ""


class CRMView(QWidget):
    def __init__(self, context: AppContext, runner: AsyncRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.runner = runner
        self.status_groups: list = []
        self.page = 1
        self.total = 0
        self.sort = "name"
        self.descending = False
        self._loading = False
        self._pending_refresh = False

        self._build_ui()
        self._load_statuses()
        self.refresh()

    # --- построение -------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("CRM")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.new_button = make_button("Новый контакт", primary=True)
        self.new_button.clicked.connect(self._create_contact)
        self.edit_button = make_button("Изменить")
        self.edit_button.clicked.connect(self._edit_contact)
        self.dnc_button = make_button("Do Not Contact")
        self.dnc_button.setToolTip("Переключить признак «не писать» у выбранных контактов")
        self.dnc_button.clicked.connect(self._toggle_dnc)
        self.trash_button = make_button("В корзину", danger=True)
        self.trash_button.clicked.connect(self._trash_selected)
        self.restore_button = make_button("Восстановить")
        self.restore_button.clicked.connect(self._restore_selected)
        self.purge_button = make_button("Удалить окончательно", danger=True)
        self.purge_button.clicked.connect(self._purge_selected)
        for button in (
            self.new_button,
            self.edit_button,
            self.dnc_button,
            self.trash_button,
            self.restore_button,
            self.purge_button,
        ):
            header.addWidget(button)
        self.restore_button.hide()
        self.purge_button.hide()
        layout.addLayout(header)

        filters = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск: имя, псевдоним, @username, email, телефон, заметки")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._schedule_search)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Все статусы", None)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)

        self.channel_combo = QComboBox()
        self.channel_combo.addItem("Все каналы", None)
        for channel in ChannelType:
            self.channel_combo.addItem(channel.label, channel)
        self.channel_combo.currentIndexChanged.connect(self._on_filter_changed)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Все источники", None)
        for source in ContactSource:
            self.source_combo.addItem(SOURCE_LABELS[source], source)
        self.source_combo.currentIndexChanged.connect(self._on_filter_changed)

        self.dnc_filter = QCheckBox("Только DNC")
        self.dnc_filter.toggled.connect(self._on_filter_changed)
        self.trash_filter = QCheckBox("Корзина")
        self.trash_filter.toggled.connect(self._on_trash_toggled)

        filters.addWidget(self.search_edit, 3)
        filters.addWidget(self.status_combo, 1)
        filters.addWidget(self.channel_combo, 1)
        filters.addWidget(self.source_combo, 1)
        filters.addWidget(self.dnc_filter)
        filters.addWidget(self.trash_filter)
        layout.addLayout(filters)

        self.banner = Banner()
        layout.addWidget(self.banner)

        self.table = QTableView()
        self.model = ContactTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(90)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 8):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 215)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 95)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 95)
        self.table.setColumnWidth(6, 95)
        self.table.setColumnWidth(7, 90)
        self.table.doubleClicked.connect(lambda _index: self._edit_contact())
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.count_label = QLabel("—")
        self.count_label.setObjectName("Hint")
        self.prev_button = make_button("← Назад")
        self.prev_button.clicked.connect(lambda: self._change_page(-1))
        self.next_button = make_button("Вперёд →")
        self.next_button.clicked.connect(lambda: self._change_page(1))
        self.import_button = make_button("Импорт CSV")
        self.import_button.clicked.connect(self._import_csv)
        self.export_button = make_button("Экспорт CSV")
        self.export_button.clicked.connect(self._export_csv)
        self.refresh_button = make_button("Обновить")
        self.refresh_button.clicked.connect(self.refresh)

        footer.addWidget(self.count_label, 1)
        footer.addWidget(self.import_button)
        footer.addWidget(self.export_button)
        footer.addWidget(self.prev_button)
        footer.addWidget(self.next_button)
        footer.addWidget(self.refresh_button)
        layout.addLayout(footer)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._reset_and_refresh)

        self.table.selectionModel().selectionChanged.connect(self._update_buttons)
        self._update_buttons()

    # --- данные -----------------------------------------------------------
    def _load_statuses(self) -> None:
        from verse.services import statuses as status_service

        def load():
            async def _inner():
                async with self.context.db.session() as session:
                    return await status_service.list_groups(session)

            return _inner()

        self.runner.run(load, self._on_statuses_loaded, self._show_error)

    def _on_statuses_loaded(self, groups) -> None:
        self.status_groups = groups
        current = self.status_combo.currentData()
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        self.status_combo.addItem("Все статусы", None)
        for group in groups:
            for status in group.statuses:
                self.status_combo.addItem(f"{group.name}: {status.name}", status.id)
        index = self.status_combo.findData(current)
        self.status_combo.setCurrentIndex(max(0, index))
        self.status_combo.blockSignals(False)

    def current_filter(self) -> ContactFilter:
        return ContactFilter(
            query=self.search_edit.text().strip() or None,
            status_ids=(
                [self.status_combo.currentData()] if self.status_combo.currentData() else []
            ),
            channel_type=self.channel_combo.currentData(),
            source=self.source_combo.currentData(),
            only_dnc=self.dnc_filter.isChecked(),
            only_deleted=self.trash_filter.isChecked(),
        )

    def refresh(self) -> None:
        if self._loading:
            # Запрос уже выполняется: не теряем запрос, повторим после ответа.
            self._pending_refresh = True
            return
        self._loading = True
        self.banner.clear()
        flt = self.current_filter()
        page = self.page
        sort = self.sort
        descending = self.descending
        self.runner.run(
            lambda: self.context.contacts.list(
                flt, page=page, page_size=PAGE_SIZE, sort=sort, descending=descending
            ),
            self._on_page,
            self._on_load_error,
        )

    def _finish_loading(self) -> None:
        self._loading = False
        if self._pending_refresh:
            self._pending_refresh = False
            self.refresh()

    def _on_page(self, page: Page) -> None:
        self._loading = False
        self.total = page.total
        self.model.set_rows(page.items)
        start = (page.page - 1) * page.page_size + 1 if page.total else 0
        end = min(page.page * page.page_size, page.total)
        self.count_label.setText(
            f"{start}–{end} из {page.total} {plural_ru(page.total, 'контакта', 'контактов', 'контактов')}"
        )
        self.prev_button.setEnabled(page.page > 1)
        self.next_button.setEnabled(page.page < page.pages)
        self._update_buttons()
        if page.total == 0:
            self.banner.show_message(
                "Ничего не найдено. Измените фильтры или создайте контакт."
            )
        self._finish_loading()

    def _on_load_error(self, error: BaseException) -> None:
        self._loading = False
        self.banner.show_message(
            getattr(error, "user_message", None) or f"Не удалось загрузить контакты: {error}"
        )
        self._finish_loading()

    def _reset_and_refresh(self) -> None:
        self.page = 1
        self.refresh()

    def _schedule_search(self) -> None:
        self._search_timer.start()

    def _on_filter_changed(self) -> None:
        self._reset_and_refresh()

    def _on_trash_toggled(self, checked: bool) -> None:
        self.trash_button.setVisible(not checked)
        self.restore_button.setVisible(checked)
        self.purge_button.setVisible(checked)
        self._reset_and_refresh()

    def _on_sort_changed(self, index: int, order: Qt.SortOrder) -> None:
        key = ContactTableModel.SORT_KEYS.get(self.model.COLUMNS[index][0], "name")
        self.sort = key
        self.descending = order == Qt.SortOrder.DescendingOrder
        self._reset_and_refresh()

    def _change_page(self, delta: int) -> None:
        self.page = max(1, self.page + delta)
        self.refresh()

    # --- выбор ------------------------------------------------------------
    def selected_rows(self) -> list[ContactRow]:
        indexes = self.table.selectionModel().selectedRows()
        rows = []
        for index in indexes:
            row = self.model.row_at(index.row())
            if row is not None:
                rows.append(row)
        return rows

    def selected_ids(self) -> list[uuid.UUID]:
        return [row.id for row in self.selected_rows()]

    def _update_buttons(self) -> None:
        has_selection = bool(self.table.selectionModel().selectedRows())
        for button in (self.edit_button, self.dnc_button):
            button.setEnabled(has_selection)
        if self.trash_filter.isChecked():
            self.restore_button.setEnabled(has_selection)
            self.purge_button.setEnabled(has_selection)
        else:
            self.trash_button.setEnabled(has_selection)

    # --- действия ---------------------------------------------------------
    def _create_contact(self) -> None:
        dialog = ContactDialog(
            detail=None,
            status_groups=self.status_groups,
            contacts_service=self.context.contacts,
            deal_service=self.context.deals,
            save_callback=self.context.contacts.create,
            runner=self.runner,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit_contact(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        target = ids[0]
        self.runner.run(
            lambda: self.context.contacts.get(target),
            lambda detail: self._open_editor(detail),
            self._show_error,
        )

    def _open_editor(self, detail: ContactDetail) -> None:
        dialog = ContactDialog(
            detail=detail,
            status_groups=self.status_groups,
            contacts_service=self.context.contacts,
            deal_service=self.context.deals,
            save_callback=lambda data: self.context.contacts.update(detail.id, data),
            runner=self.runner,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _toggle_dnc(self) -> None:
        rows = self.selected_rows()
        if not rows:
            return
        values = {row.do_not_contact for row in rows}
        target = not (len(values) == 1 and True in values)
        ids = [row.id for row in rows]
        self.runner.run(
            lambda: self.context.contacts.set_dnc(ids, target, None),
            lambda count: self._after_bulk(f"Do Not Contact: {count}"),
            self._show_error,
        )

    def _trash_selected(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        if (
            QMessageBox.question(self, "Корзина", f"Переместить в корзину: {len(ids)}?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.runner.run(
            lambda: self.context.contacts.bulk_trash(ids),
            lambda count: self._after_bulk(f"В корзину: {count}"),
            self._show_error,
        )

    def _restore_selected(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        self.runner.run(
            lambda: self.context.contacts.bulk_restore(ids),
            lambda count: self._after_bulk(f"Восстановлено: {count}"),
            self._show_error,
        )

    def _purge_selected(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        if (
            QMessageBox.warning(
                self,
                "Окончательное удаление",
                f"Удалить без возможности восстановления: {len(ids)}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.runner.run(
            lambda: self.context.contacts.bulk_purge(ids),
            lambda count: self._after_bulk(f"Удалено окончательно: {count}"),
            self._show_error,
        )

    def _after_bulk(self, message: str) -> None:
        self.banner.show_message(message)
        self.refresh()

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт контактов", str(Path.home()), "CSV (*.csv);;Все файлы (*)"
        )
        if not path:
            return
        try:
            preview = transfer_service.preview(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Импорт", getattr(exc, "user_message", str(exc)))
            return
        dialog = ImportDialog(preview, os.path.basename(path), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        mapping = dialog.mapping()
        self.runner.run(
            lambda: transfer_service.import_contacts(self.context.db, path, mapping),
            self._on_imported,
            self._show_error,
        )

    def _on_imported(self, report) -> None:
        text = report.summary()
        if report.errors:
            text += "\n\n" + "\n".join(report.errors[:15])
            if len(report.errors) > 15:
                text += f"\n… и ещё {len(report.errors) - 15}"
        QMessageBox.information(self, "Импорт завершён", text)
        self._reset_and_refresh()

    def _export_csv(self) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        default = str(self.context.settings.exports_dir / f"contacts-{stamp}.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт контактов", default, "CSV (*.csv)"
        )
        if not path:
            return
        ids = self.selected_ids() or None
        self.runner.run(
            lambda: transfer_service.export_contacts(self.context.db, path, ids),
            lambda count: QMessageBox.information(
                self, "Экспорт завершён", f"Экспортировано контактов: {count}\n{path}"
            ),
            self._show_error,
        )

    def _show_error(self, error: BaseException) -> None:
        message = getattr(error, "user_message", None) or str(error)
        if not self.isVisible():
            # Экран уже закрыт (например, приложение завершается) — не показываем модалку.
            self.banner.show_message(message)
            return
        QMessageBox.critical(self, "Ошибка", message)
