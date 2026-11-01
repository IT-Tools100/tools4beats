"""Импорт и экспорт CSV: идемпотентность и обратимость."""

from __future__ import annotations

from pathlib import Path

from verse.domain.filters import ContactFilter
from verse.services import transfer as transfer_service


def _write_csv(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


async def test_import_creates_contacts(db, contacts, tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "in.csv",
        "Name,Email,Instagram,Notes\n"
        "Alpha,alpha@mail.com,@alpha,первый\n"
        "Beta,,@beta,второй\n",
    )
    report = await transfer_service.import_contacts(db, path)

    assert report.created == 2
    assert (await contacts.list(ContactFilter())).total == 2

    alpha = (await contacts.list(ContactFilter(query="alpha"))).items[0]
    assert alpha.channels[0].normalized_value == "alpha@mail.com"


async def test_reimport_is_idempotent(db, contacts, tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path / "in.csv",
        "Name,Email\nAlpha,alpha@mail.com\nBeta,beta@mail.com\n",
    )
    first = await transfer_service.import_contacts(db, path)
    assert first.created == 2

    second = await transfer_service.import_contacts(db, path)
    assert second.created == 0
    assert second.updated == 0
    assert second.unchanged == 2
    assert (await contacts.list(ContactFilter())).total == 2


async def test_import_updates_existing_by_channel(db, contacts, tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "a.csv", "Name,Email\nAlpha,alpha@mail.com\n")
    await transfer_service.import_contacts(db, path)

    updated = _write_csv(
        tmp_path / "b.csv", "Name,Email,Notes\nAlpha Updated,alpha@mail.com,новые заметки\n"
    )
    report = await transfer_service.import_contacts(db, updated)

    assert report.created == 0
    assert report.updated == 1
    detail = (await contacts.list(ContactFilter())).items[0]
    assert detail.display_name == "Alpha"

    full = await contacts.get(detail.id)
    assert full.notes == "новые заметки"


async def test_import_skips_rows_without_name(db, tmp_path: Path) -> None:
    path = _write_csv(tmp_path / "bad.csv", "Name,Email\n,noname@mail.com\nGood,good@mail.com\n")
    report = await transfer_service.import_contacts(db, path)

    assert report.created == 1
    assert any("пустое имя" in error for error in report.errors)


async def test_export_roundtrip(db, contacts, tmp_path: Path) -> None:
    await contacts.create(
        contact_in_simple("Export Artist", "export@mail.com", "@exportartist")
    )
    out = tmp_path / "out.csv"
    exported = await transfer_service.export_contacts(db, out)

    assert exported == 1
    text = out.read_text(encoding="utf-8-sig")
    assert "Export Artist" in text
    assert "export@mail.com" in text

    # Повторный импорт собственного экспорта не должен создавать дубликатов.
    report = await transfer_service.import_contacts(db, out)
    assert report.created == 0
    assert report.conflicts == 0
    assert (await contacts.list(ContactFilter())).total == 1


def contact_in_simple(name: str, email: str, instagram: str):
    from tests.factories import contact_in

    return contact_in(name, email=email, instagram=instagram)
