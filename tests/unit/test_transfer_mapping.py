"""Автоподбор колонок CSV и определение разделителя."""

from __future__ import annotations

from pathlib import Path

from verse.services.transfer import auto_mapping, preview, read_table


def test_auto_mapping_english() -> None:
    mapping = auto_mapping(["Name", "Email", "Instagram", "Notes"])
    assert mapping["display_name"] == 0
    assert mapping["email"] == 1
    assert mapping["instagram"] == 2
    assert mapping["notes"] == 3


def test_auto_mapping_russian() -> None:
    mapping = auto_mapping(["Имя", "Почта", "Телефон", "Заметки"])
    assert mapping["display_name"] == 0
    assert mapping["email"] == 1
    assert mapping["phone"] == 2
    assert mapping["notes"] == 3


def test_semicolon_delimiter(tmp_path: Path) -> None:
    path = tmp_path / "contacts.csv"
    path.write_text("Name;Email\nArtist;artist@mail.com\n", encoding="utf-8")
    headers, rows = read_table(path)
    assert headers == ["Name", "Email"]
    assert rows == [["Artist", "artist@mail.com"]]


def test_preview_counts_rows(tmp_path: Path) -> None:
    path = tmp_path / "contacts.csv"
    path.write_text("Name,Email\nA,a@b.com\nB,b@b.com\n", encoding="utf-8")
    result = preview(path)
    assert result.total_rows == 2
    assert result.mapping["display_name"] == 0
