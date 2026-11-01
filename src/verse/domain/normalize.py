"""Нормализация значений каналов связи.

Одна и та же функция используется при ручном вводе и при импорте —
это единственный способ гарантировать, что дубликаты ловятся уникальным
индексом `(channel_type, normalized_value)`.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from verse.domain.enums import PHONE_CHANNELS, ChannelType
from verse.errors import ValidationError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_DIGITS_RE = re.compile(r"\d+")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def normalize_email(raw: str) -> str:
    value = raw.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValidationError(f"Некорректный email: {raw!r}")
    return value


def normalize_phone(raw: str) -> str:
    """Приводит номер к виду `+<цифры>` (без полноценного парсинга стран)."""
    raw = raw.strip()
    has_plus = raw.startswith("+")
    digits = "".join(_DIGITS_RE.findall(raw))
    if len(digits) < 7:
        raise ValidationError(f"Некорректный телефон: {raw!r}")
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return ("+" if has_plus or len(digits) > 10 else "") + digits


def normalize_handle(raw: str, *, host: str | None = None) -> str:
    """Instagram/Telegram-хэндл: без пробелов, без `@`, без URL."""
    value = raw.strip()
    if host and value.lower().startswith(("http://", "https://")):
        parsed = urlparse(value)
        if host not in parsed.netloc.lower():
            raise ValidationError(f"Ссылка не относится к {host}: {raw!r}")
        value = parsed.path.strip("/").split("/")[0]
    value = value.lstrip("@").strip().rstrip("/")
    if not value:
        raise ValidationError("Пустое значение канала")
    if " " in value:
        raise ValidationError(f"Хэндл не может содержать пробелы: {raw!r}")
    return value.lower()


def normalize_spotify(raw: str) -> str:
    """Принимает URL, URI или ID артиста."""
    value = raw.strip()
    if value.lower().startswith("spotify:artist:"):
        return value.split(":")[-1]
    if value.lower().startswith(("http://", "https://")):
        parsed = urlparse(value)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "artist":
            return parts[1]
        return value
    return value


def normalize_url(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValidationError("Пустой URL")
    if not _URL_RE.match(value):
        value = "https://" + value
    return value


def normalize_channel_value(channel_type: ChannelType, raw: str) -> str:
    """Единая точка нормализации. Бросает ValidationError на мусор."""
    if not raw or not raw.strip():
        raise ValidationError("Значение канала не может быть пустым")

    if channel_type is ChannelType.EMAIL:
        return normalize_email(raw)
    if channel_type in PHONE_CHANNELS:
        return normalize_phone(raw)
    if channel_type in (ChannelType.INSTAGRAM, ChannelType.TELEGRAM):
        host = "instagram.com" if channel_type is ChannelType.INSTAGRAM else "t.me"
        return normalize_handle(raw, host=host)
    if channel_type is ChannelType.SPOTIFY:
        return normalize_spotify(raw)
    if channel_type in (ChannelType.YOUTUBE, ChannelType.SOUNDCLOUD):
        host = "youtube.com" if channel_type is ChannelType.YOUTUBE else "soundcloud.com"
        if raw.lower().startswith(("http://", "https://")):
            return normalize_url(raw)
        return normalize_handle(raw, host=host)
    if channel_type is ChannelType.DISCORD:
        return raw.strip().lstrip("@").lower()
    if channel_type is ChannelType.OTHER:
        return raw.strip()
    raise ValidationError(f"Неподдерживаемый канал: {channel_type}")


def display_value(channel_type: ChannelType, normalized: str, raw: str | None = None) -> str:
    if channel_type is ChannelType.INSTAGRAM:
        return f"@{normalized}"
    return raw or normalized
