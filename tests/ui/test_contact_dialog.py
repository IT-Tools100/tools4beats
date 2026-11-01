"""Диалог контакта: сборка DTO, заполнение из деталей, взаимоисключение статусов."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from PySide6.QtWidgets import QDialog

from verse.domain.dto import ChannelView, ContactDetail, NoteView, StatusRef
from verse.domain.dto import StatusGroupView, StatusOption
from verse.domain.enums import ChannelType, ContactSource
from verse.ui.bridge import InertRunner
from verse.ui.dialogs.contact_dialog import ContactDialog


def _groups() -> list[StatusGroupView]:
    funnel_statuses = [
        StatusOption(
            id=uuid.uuid4(), name="New", color="#111111",
            group_name="Воронка", group_slug="funnel", allows_multiple=False,
        ),
        StatusOption(
            id=uuid.uuid4(), name="Contacted", color="#222222",
            group_name="Воронка", group_slug="funnel", allows_multiple=False,
        ),
    ]
    interest_statuses = [
        StatusOption(
            id=uuid.uuid4(), name="Hot", color="#333333",
            group_name="Заинтересованность", group_slug="interest", allows_multiple=True,
        )
    ]
    return [
        StatusGroupView(
            id=uuid.uuid4(), name="Воронка", slug="funnel", color="#111111",
            allows_multiple=False, statuses=funnel_statuses,
        ),
        StatusGroupView(
            id=uuid.uuid4(), name="Заинтересованность", slug="interest", color="#333333",
            allows_multiple=True, statuses=interest_statuses,
        ),
    ]


def _dialog(qtbot) -> ContactDialog:
    dialog = ContactDialog(
        detail=None,
        status_groups=_groups(),
        contacts_service=None,
        deal_service=None,
        save_callback=lambda data: data,
        runner=InertRunner(),
    )
    qtbot.addWidget(dialog)
    return dialog


def test_collect_builds_contact_in(qtbot) -> None:
    dialog = _dialog(qtbot)
    dialog.display_name_edit.setText("  Dialog Artist  ")
    dialog.stage_name_edit.setText("DA")
    dialog.notes_edit.setPlainText("заметка")
    dialog._add_channel_row(ChannelType.EMAIL, "Dialog@Test.com")

    data = dialog._collect()

    assert data is not None
    assert data.display_name == "Dialog Artist"
    assert data.stage_name == "DA"
    assert data.notes == "заметка"
    assert len(data.channels) == 1
    assert data.channels[0].channel_type is ChannelType.EMAIL
    assert data.channels[0].is_primary is True
    assert data.source is ContactSource.MANUAL


def test_channel_rows_skip_empty_values(qtbot) -> None:
    dialog = _dialog(qtbot)
    dialog.display_name_edit.setText("No Channels")
    dialog._add_channel_row(ChannelType.EMAIL, "")
    dialog._add_channel_row(ChannelType.INSTAGRAM, "")

    data = dialog._collect()

    assert data is not None
    assert data.channels == []


def test_single_select_status_group(qtbot) -> None:
    dialog = _dialog(qtbot)
    buttons = list(dialog._status_buttons.values())
    first, second = buttons[0], buttons[1]

    first.setChecked(True)
    second.setChecked(True)

    assert second.isChecked() is True
    assert first.isChecked() is False


def test_fill_from_detail(qtbot) -> None:
    detail = ContactDetail(
        id=uuid.uuid4(),
        display_name="Existing Artist",
        real_name=None,
        stage_name="EX",
        source=ContactSource.SPOTIFY,
        genres="trap",
        references=None,
        notes="старая заметка",
        do_not_contact=True,
        do_not_contact_reason="просил",
        last_contact_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        next_action_at=None,
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        is_deleted=False,
        channels=[
            ChannelView(
                id=uuid.uuid4(), channel_type=ChannelType.EMAIL,
                raw_value="ex@mail.com", normalized_value="ex@mail.com",
                label=None, is_primary=True,
            )
        ],
        statuses=[
            StatusRef(
                id=uuid.uuid4(), name="New", color="#fff",
                group_name="Воронка", group_slug="funnel",
            )
        ],
        deals=[],
        notes_history=[
            NoteView(
                id=uuid.uuid4(),
                body="отправил пак",
                author_kind="user",
                created_at=datetime(2026, 10, 2, 10, 0, tzinfo=UTC),
            )
        ],
    )
    dialog = ContactDialog(
        detail=detail,
        status_groups=_groups(),
        contacts_service=None,
        deal_service=None,
        save_callback=lambda data: data,
        runner=InertRunner(),
    )
    qtbot.addWidget(dialog)

    collected = dialog._collect()
    assert collected is not None
    assert collected.display_name == "Existing Artist"
    assert collected.source is ContactSource.SPOTIFY
    assert collected.do_not_contact is True
    assert collected.channels[0].value == "ex@mail.com"
    assert dialog.last_contact_check.isChecked() is True
    assert "отправил пак" in dialog.notes_list.item(0).text()

    dialog.reject()
    assert dialog.result() == QDialog.DialogCode.Rejected
