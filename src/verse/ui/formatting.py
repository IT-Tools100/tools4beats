"""Форматирование значений для интерфейса."""

from __future__ import annotations

import datetime as dt
from urllib.parse import urlsplit, urlunsplit


def format_dt(value: dt.datetime | None, *, with_time: bool = True) -> str:
    if value is None:
        return "—"
    local = value.astimezone()
    return local.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")


def to_utc(value: dt.datetime | None) -> dt.datetime | None:
    """Наивное локальное время из QDateTime → aware UTC для БД."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.astimezone()
    return value.astimezone(dt.UTC)


def from_utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    return value.astimezone()


def mask_dsn(url: str) -> str:
    """Скрывает пароль в строке подключения для экрана настроек/логов."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    if parts.password:
        netloc = f"{parts.username}:***@{parts.hostname}"
        if parts.port:
            netloc += f":{parts.port}"
        parts = parts._replace(netloc=netloc)
    return urlunsplit(parts)


def plural_ru(count: int, one: str, few: str, many: str) -> str:
    count = abs(count) % 100
    if 11 <= count <= 19:
        return many
    count %= 10
    if count == 1:
        return one
    if 2 <= count <= 4:
        return few
    return many


def to_qdatetime(value: dt.datetime | None):
    """UTC из БД → QDateTime в локальном времени пользователя."""
    from PySide6.QtCore import QDateTime

    if value is None:
        return QDateTime.currentDateTime()
    return QDateTime(value.astimezone().replace(tzinfo=None))
