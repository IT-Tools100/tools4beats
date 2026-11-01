"""Доменные исключения.

Правило: сервисы бросают только эти ошибки; UI показывает `user_message`,
а технические подробности уходят в лог.
"""

from __future__ import annotations


class VerseError(Exception):
    """Базовая ошибка приложения."""

    user_message = "Произошла ошибка."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.user_message)
        if message:
            self.user_message = message


class ValidationError(VerseError):
    user_message = "Некорректные данные."


class NotFoundError(VerseError):
    user_message = "Запись не найдена."


class DuplicateError(VerseError):
    user_message = "Такая запись уже существует."


class DuplicateChannelError(DuplicateError):
    """Канал уже привязан к другому контакту."""

    user_message = "Этот канал связи уже используется другим контактом."

    def __init__(self, channel_type: str, value: str, contact_id: object) -> None:
        super().__init__(
            f"Канал {channel_type}:{value} уже принадлежит контакту {contact_id}."
        )
        self.channel_type = channel_type
        self.value = value
        self.contact_id = contact_id


class ConflictError(VerseError):
    user_message = "Конфликт данных."


class ImportError_(VerseError):
    user_message = "Не удалось импортировать файл."


class DatabaseUnavailableError(VerseError):
    user_message = "Нет подключения к PostgreSQL. Запустите базу командой `make db-up`."
