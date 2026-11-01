"""Диалог создания и редактирования контакта."""

from __future__ import annotations

import uuid
from decimal import Decimal

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from verse.domain.dto import (
    ChannelIn,
    ContactDetail,
    ContactIn,
    DealIn,
    DealView,
    PaymentIn,
)
from verse.domain.enums import (
    CHANNEL_LABELS,
    DEAL_STAGE_LABELS,
    SOURCE_LABELS,
    ChannelType,
    ContactSource,
    DealStage,
)
from verse.ui.formatting import format_dt, to_qdatetime
from verse.ui.widgets.common import make_button

CURRENCIES = ["USD", "EUR", "RUB", "GBP"]


class ChannelRow(QWidget):
    def __init__(self, channel_type: ChannelType = ChannelType.INSTAGRAM, value: str = "",
                 label: str = "", primary: bool = False) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.type_combo = QComboBox()
        for channel in ChannelType:
            self.type_combo.addItem(CHANNEL_LABELS[channel], channel)
        self.type_combo.setCurrentIndex(self.type_combo.findData(channel_type))

        self.value_edit = QLineEdit(value)
        self.value_edit.setPlaceholderText("значение")
        self.label_edit = QLineEdit(label)
        self.label_edit.setPlaceholderText("метка")
        self.label_edit.setMaximumWidth(160)
        self.primary_check = QCheckBox("основной")
        self.primary_check.setChecked(primary)

        layout.addWidget(self.type_combo, 2)
        layout.addWidget(self.value_edit, 4)
        layout.addWidget(self.label_edit, 2)
        layout.addWidget(self.primary_check)


class DealEditDialog(QDialog):
    def __init__(self, deal: DealView | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Сделка" if deal is None else "Изменить сделку")
        self.setMinimumWidth(420)
        form = QFormLayout(self)

        self.title_edit = QLineEdit(deal.title if deal else "")
        self.title_edit.setPlaceholderText("например, эксклюзив на бит")
        self.stage_combo = QComboBox()
        for stage in DealStage:
            self.stage_combo.addItem(DEAL_STAGE_LABELS[stage], stage)
        if deal:
            self.stage_combo.setCurrentIndex(self.stage_combo.findData(deal.stage))

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 1_000_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setGroupSeparatorShown(True)
        if deal and deal.amount_expected is not None:
            self.amount_spin.setValue(float(deal.amount_expected))

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(CURRENCIES)
        if deal:
            index = self.currency_combo.findText(deal.currency)
            if index >= 0:
                self.currency_combo.setCurrentIndex(index)

        self.notes_edit = QPlainTextEdit(deal.notes if deal else "")
        self.notes_edit.setFixedHeight(70)

        form.addRow("Название", self.title_edit)
        form.addRow("Стадия", self.stage_combo)
        form.addRow("Ожидаемая сумма", self.amount_spin)
        form.addRow("Валюта", self.currency_combo)
        form.addRow("Заметки", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate(self) -> None:
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Сделка", "Укажите название сделки.")
            return
        self.accept()

    def to_dto(self) -> DealIn:
        amount = Decimal(str(round(self.amount_spin.value(), 2)))
        return DealIn(
            title=self.title_edit.text().strip(),
            stage=self.stage_combo.currentData(),
            amount_expected=amount if amount > 0 else None,
            currency=self.currency_combo.currentText(),
            notes=self.notes_edit.toPlainText().strip() or None,
        )


class PaymentDialog(QDialog):
    def __init__(self, default_currency: str = "USD", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Платёж")
        self.setMinimumWidth(380)
        form = QFormLayout(self)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 1_000_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setValue(100.0)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(CURRENCIES)
        index = self.currency_combo.findText(default_currency)
        if index >= 0:
            self.currency_combo.setCurrentIndex(index)

        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy HH:mm")

        self.method_edit = QLineEdit()
        self.method_edit.setPlaceholderText("например, PayPal / карта")

        form.addRow("Сумма", self.amount_spin)
        form.addRow("Валюта", self.currency_combo)
        form.addRow("Дата", self.date_edit)
        form.addRow("Способ", self.method_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def to_dto(self) -> PaymentIn:
        return PaymentIn(
            amount=Decimal(str(round(self.amount_spin.value(), 2))),
            currency=self.currency_combo.currentText(),
            paid_at=self.date_edit.dateTime().toPython(),
            method=self.method_edit.text().strip() or None,
        )


class ContactDialog(QDialog):
    """Создание и редактирование контакта.

    `detail=None` — создание. Сохранение выполняет переданный `save_callback`,
    который возвращает идентификатор контакта; диалог только собирает данные.
    """

    def __init__(
        self,
        *,
        detail: ContactDetail | None,
        status_groups,
        contacts_service,
        deal_service,
        save_callback,
        runner,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.detail = detail
        self.status_groups = status_groups
        self.contacts_service = contacts_service
        self.deal_service = deal_service
        self.save_callback = save_callback
        self.runner = runner
        self.saved_id: uuid.UUID | None = detail.id if detail else None
        self._deal_dtos: list[DealView] = list(detail.deals) if detail else []

        self.setWindowTitle("Новый контакт" if detail is None else "Контакт")
        self.setMinimumSize(760, 620)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_main_tab(), "Основное")
        self.tabs.addTab(self._build_channels_tab(), "Каналы")
        self.tabs.addTab(self._build_status_tab(), "Статусы")
        self.tabs.addTab(self._build_notes_tab(), "Заметки")
        if detail is not None:
            self.tabs.addTab(self._build_deals_tab(), "Сделки")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)

        if detail:
            self._fill(detail)

    # --- построение вкладок ----------------------------------------------
    def _build_main_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.display_name_edit = QLineEdit()
        self.display_name_edit.setPlaceholderText("Имя контакта или артиста — обязательно")
        self.stage_name_edit = QLineEdit()
        self.real_name_edit = QLineEdit()

        self.source_combo = QComboBox()
        for source in ContactSource:
            self.source_combo.addItem(SOURCE_LABELS[source], source)

        self.genres_edit = QLineEdit()
        self.genres_edit.setPlaceholderText("например, trap, plugg")
        self.references_edit = QLineEdit()
        self.references_edit.setPlaceholderText("на кого ориентируется артист")

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setFixedHeight(90)

        self.dnc_check = QCheckBox("Do Not Contact — не писать")
        self.dnc_reason_edit = QLineEdit()
        self.dnc_reason_edit.setPlaceholderText("причина")

        self.last_contact_check = QCheckBox("последний контакт")
        self.last_contact_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.last_contact_edit.setCalendarPopup(True)
        self.last_contact_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.last_contact_edit.setEnabled(False)
        self.last_contact_check.toggled.connect(self.last_contact_edit.setEnabled)

        self.next_action_check = QCheckBox("следующее действие")
        self.next_action_edit = QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.next_action_edit.setCalendarPopup(True)
        self.next_action_edit.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.next_action_edit.setEnabled(False)
        self.next_action_check.toggled.connect(self.next_action_edit.setEnabled)

        last_row = QWidget()
        last_layout = QHBoxLayout(last_row)
        last_layout.setContentsMargins(0, 0, 0, 0)
        last_layout.addWidget(self.last_contact_check)
        last_layout.addWidget(self.last_contact_edit)

        next_row = QWidget()
        next_layout = QHBoxLayout(next_row)
        next_layout.setContentsMargins(0, 0, 0, 0)
        next_layout.addWidget(self.next_action_check)
        next_layout.addWidget(self.next_action_edit)

        dnc_row = QWidget()
        dnc_layout = QHBoxLayout(dnc_row)
        dnc_layout.setContentsMargins(0, 0, 0, 0)
        dnc_layout.addWidget(self.dnc_check)
        dnc_layout.addWidget(self.dnc_reason_edit, 1)

        form.addRow("Имя *", self.display_name_edit)
        form.addRow("Псевдоним", self.stage_name_edit)
        form.addRow("Настоящее имя", self.real_name_edit)
        form.addRow("Источник", self.source_combo)
        form.addRow("Жанры", self.genres_edit)
        form.addRow("Референсы", self.references_edit)
        form.addRow("Заметки", self.notes_edit)
        form.addRow("Последний контакт", last_row)
        form.addRow("Следующее действие", next_row)
        form.addRow("Исключение", dnc_row)
        return widget

    def _build_channels_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        hint = QLabel(
            "Значения нормализуются автоматически: один и тот же email или телефон "
            "нельзя привязать к двум контактам."
        )
        hint.setWordWrap(True)
        hint.setObjectName("Hint")
        layout.addWidget(hint)

        self.channels_container = QWidget()
        self.channels_layout = QVBoxLayout(self.channels_container)
        self.channels_layout.setContentsMargins(0, 0, 0, 0)
        self.channels_layout.setSpacing(6)
        self.channels_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.channels_container)
        layout.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        add_button = make_button("Добавить канал")
        add_button.clicked.connect(lambda: self._add_channel_row())
        buttons.addWidget(add_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._channel_rows: list[ChannelRow] = []
        return widget

    def _add_channel_row(
        self,
        channel_type: ChannelType = ChannelType.INSTAGRAM,
        value: str = "",
        label: str = "",
        primary: bool = False,
    ) -> None:
        row = ChannelRow(channel_type, value, label, primary)
        remove = make_button("Удалить", danger=True)
        remove.clicked.connect(lambda: self._remove_channel_row(row))
        holder = QWidget()
        holder_layout = QHBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addWidget(row, 1)
        holder_layout.addWidget(remove)
        row.setProperty("holder", holder)
        row.primary_check.toggled.connect(lambda checked, r=row: self._exclusive_primary(r, checked))
        self._channel_rows.append(row)
        self.channels_layout.insertWidget(len(self._channel_rows) - 1, holder)

    def _exclusive_primary(self, row: ChannelRow, checked: bool) -> None:
        """Основной канал может быть только один."""
        if not checked:
            return
        for other in self._channel_rows:
            if other is not row and other.primary_check.isChecked():
                other.primary_check.blockSignals(True)
                other.primary_check.setChecked(False)
                other.primary_check.blockSignals(False)

    def _remove_channel_row(self, row: ChannelRow) -> None:
        if row in self._channel_rows:
            self._channel_rows.remove(row)
        holder = row.property("holder")
        if holder is not None:
            holder.setParent(None)
            holder.deleteLater()

    def _build_status_tab(self) -> QWidget:
        container = QWidget()
        outer = QVBoxLayout(container)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)

        self._status_buttons: dict[uuid.UUID, QCheckBox] = {}
        self._status_groups_widgets: list[tuple[QGroupBox, list[uuid.UUID]]] = []

        if not self.status_groups:
            layout.addWidget(QLabel("Статусы не настроены."))
        for group in self.status_groups:
            box = QGroupBox(group.name)
            box_layout = QVBoxLayout(box)
            ids: list[uuid.UUID] = []
            for status in group.statuses:
                check = QCheckBox(status.name)
                check.setProperty("status_id", status.id)
                box_layout.addWidget(check)
                self._status_buttons[status.id] = check
                ids.append(status.id)
                if not group.allows_multiple:
                    check.toggled.connect(
                        lambda checked, sid=status.id, group_ids=list(ids): self._single_select(
                            checked, sid, group_ids
                        )
                    )
            self._status_groups_widgets.append((box, ids))
            layout.addWidget(box)
        layout.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return container

    def _single_select(self, checked: bool, status_id: uuid.UUID, group_ids: list[uuid.UUID]) -> None:
        if not checked:
            return
        # Группа формируется динамически, поэтому берём все статусы того же QGroupBox.
        sender = self._status_buttons[status_id]
        parent = sender.parentWidget()
        for other in self._status_buttons.values():
            if other is not sender and other.parentWidget() is parent and other.isChecked():
                other.blockSignals(True)
                other.setChecked(False)
                other.blockSignals(False)

    def _build_notes_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.notes_list = QListWidget()
        layout.addWidget(self.notes_list, 1)

        row = QHBoxLayout()
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("Новая заметка: что обсудили, что отправить дальше…")
        self.note_input.returnPressed.connect(self._add_note)
        self.note_add_button = make_button("Добавить заметку", primary=True)
        self.note_add_button.clicked.connect(self._add_note)
        row.addWidget(self.note_input, 1)
        row.addWidget(self.note_add_button)
        layout.addLayout(row)

        self.notes_hint = QLabel(
            "Сохраните контакт, чтобы добавлять заметки с историей."
            if self.detail is None
            else "Заметки сохраняются отдельными записями с датой и автором."
        )
        self.notes_hint.setObjectName("Hint")
        layout.addWidget(self.notes_hint)

        if self.detail is None:
            self.note_input.setEnabled(False)
            self.note_add_button.setEnabled(False)
        else:
            self._refresh_notes()
        return widget

    def _refresh_notes(self) -> None:
        if not hasattr(self, "notes_list"):
            return
        self.notes_list.clear()
        if self.detail is None:
            return
        for note in self.detail.notes_history:
            self.notes_list.addItem(
                f"{format_dt(note.created_at)}  ·  {note.body}"
            )
        if not self.detail.notes_history:
            self.notes_list.addItem("Пока нет заметок.")

    def _add_note(self) -> None:
        if self.detail is None:
            return
        body = self.note_input.text().strip()
        if not body:
            return
        self.runner.run(
            lambda: self.contacts_service.add_note(self.detail.id, body),
            lambda _result: self._reload_detail(clear_note=True),
            self._show_error,
        )

    def _build_deals_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.deals_table = QTableWidget(0, 4)
        self.deals_table.setHorizontalHeaderLabels(
            ["Название", "Стадия", "Ожидается", "Оплачено"]
        )
        self.deals_table.horizontalHeader().setStretchLastSection(True)
        self.deals_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.deals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.deals_table, 1)

        buttons = QHBoxLayout()
        add_deal = make_button("Добавить сделку")
        add_deal.clicked.connect(self._add_deal)
        edit_deal = make_button("Изменить")
        edit_deal.clicked.connect(self._edit_deal)
        delete_deal = make_button("Удалить", danger=True)
        delete_deal.clicked.connect(self._delete_deal)
        add_payment = make_button("Добавить платёж")
        add_payment.clicked.connect(self._add_payment)
        for button in (add_deal, edit_deal, delete_deal, add_payment):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self._refresh_deals()
        return widget

    # --- сделки -----------------------------------------------------------
    def _refresh_deals(self) -> None:
        self.deals_table.setRowCount(len(self._deal_dtos))
        for row, deal in enumerate(self._deal_dtos):
            paid = deal.paid_total
            values = [
                deal.title,
                DEAL_STAGE_LABELS[deal.stage],
                f"{deal.amount_expected} {deal.currency}" if deal.amount_expected else "—",
                f"{paid} {deal.currency}" if paid else "—",
            ]
            for column, value in enumerate(values):
                self.deals_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _selected_deal(self) -> DealView | None:
        row = self.deals_table.currentRow()
        if 0 <= row < len(self._deal_dtos):
            return self._deal_dtos[row]
        return None

    def _add_deal(self) -> None:
        dialog = DealEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.runner.run(
                lambda: self.deal_service.create(self.detail.id, dialog.to_dto()),
                lambda _result: self._reload_deals(),
                self._show_error,
            )

    def _edit_deal(self) -> None:
        deal = self._selected_deal()
        if deal is None:
            return
        dialog = DealEditDialog(deal, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.runner.run(
                lambda: self.deal_service.update(deal.id, dialog.to_dto()),
                lambda _result: self._reload_deals(),
                self._show_error,
            )

    def _delete_deal(self) -> None:
        deal = self._selected_deal()
        if deal is None:
            return
        if QMessageBox.question(self, "Удаление", f"Удалить сделку «{deal.title}»?") != QMessageBox.StandardButton.Yes:
            return
        self.runner.run(
            lambda: self.deal_service.delete(deal.id),
            lambda _result: self._reload_deals(),
            self._show_error,
        )

    def _add_payment(self) -> None:
        deal = self._selected_deal()
        if deal is None:
            QMessageBox.information(self, "Платёж", "Выберите сделку в таблице.")
            return
        dialog = PaymentDialog(deal.currency, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.runner.run(
                lambda: self.deal_service.add_payment(deal.id, dialog.to_dto()),
                lambda _result: self._reload_deals(),
                self._show_error,
            )

    def _reload_deals(self) -> None:
        self._reload_detail()

    def _reload_detail(self, *, clear_note: bool = False) -> None:
        self.runner.run(
            lambda: self.contacts_service.get(self.detail.id),
            lambda detail: self._on_detail_reloaded(detail, clear_note=clear_note),
            self._show_error,
        )

    def _on_detail_reloaded(self, detail: ContactDetail, *, clear_note: bool = False) -> None:
        self.detail = detail
        self._deal_dtos = list(detail.deals)
        if hasattr(self, "deals_table"):
            self._refresh_deals()
        self._refresh_notes()
        if clear_note and hasattr(self, "note_input"):
            self.note_input.clear()

    # --- данные -----------------------------------------------------------
    def _fill(self, detail: ContactDetail) -> None:
        self.display_name_edit.setText(detail.display_name)
        self.stage_name_edit.setText(detail.stage_name or "")
        self.real_name_edit.setText(detail.real_name or "")
        index = self.source_combo.findData(detail.source)
        if index >= 0:
            self.source_combo.setCurrentIndex(index)
        self.genres_edit.setText(detail.genres or "")
        self.references_edit.setText(detail.references or "")
        self.notes_edit.setPlainText(detail.notes or "")
        self.dnc_check.setChecked(detail.do_not_contact)
        self.dnc_reason_edit.setText(detail.do_not_contact_reason or "")

        if detail.last_contact_at:
            self.last_contact_check.setChecked(True)
            self.last_contact_edit.setDateTime(to_qdatetime(detail.last_contact_at))
        if detail.next_action_at:
            self.next_action_check.setChecked(True)
            self.next_action_edit.setDateTime(to_qdatetime(detail.next_action_at))

        for channel in detail.channels:
            self._add_channel_row(
                channel.channel_type, channel.normalized_value, channel.label or "", channel.is_primary
            )
        if not detail.channels:
            self._add_channel_row()

        for status_id, check in self._status_buttons.items():
            check.setChecked(any(status.id == status_id for status in detail.statuses))

    def _collect(self) -> ContactIn | None:
        name = self.display_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Контакт", "Укажите имя контакта.")
            self.tabs.setCurrentIndex(0)
            return None

        channels: list[ChannelIn] = []
        for row in self._channel_rows:
            value = row.value_edit.text().strip()
            if not value:
                continue
            channels.append(
                ChannelIn(
                    channel_type=row.type_combo.currentData(),
                    value=value,
                    label=row.label_edit.text().strip() or None,
                    is_primary=row.primary_check.isChecked(),
                )
            )
        if channels and not any(channel.is_primary for channel in channels):
            channels[0].is_primary = True

        status_ids = [sid for sid, check in self._status_buttons.items() if check.isChecked()]

        return ContactIn(
            display_name=name,
            stage_name=self.stage_name_edit.text().strip() or None,
            real_name=self.real_name_edit.text().strip() or None,
            source=self.source_combo.currentData(),
            genres=self.genres_edit.text().strip() or None,
            references=self.references_edit.text().strip() or None,
            notes=self.notes_edit.toPlainText().strip() or None,
            do_not_contact=self.dnc_check.isChecked(),
            do_not_contact_reason=self.dnc_reason_edit.text().strip() or None,
            last_contact_at=(
                self.last_contact_edit.dateTime().toPython()
                if self.last_contact_check.isChecked()
                else None
            ),
            next_action_at=(
                self.next_action_edit.dateTime().toPython()
                if self.next_action_check.isChecked()
                else None
            ),
            channels=channels,
            status_ids=status_ids,
        )

    def _save(self) -> None:
        data = self._collect()
        if data is None:
            return
        self.runner.run(
            lambda: self.save_callback(data),
            self._on_saved,
            self._show_error,
        )

    def _on_saved(self, result) -> None:
        if isinstance(result, uuid.UUID):
            self.saved_id = result
        self.accept()

    def _show_error(self, error: BaseException) -> None:
        message = getattr(error, "user_message", None) or str(error)
        QMessageBox.critical(self, "Ошибка", message)
