"""Перечисления предметной области.

Значения хранятся в БД в нижнем регистре (values_callable в db.base).
"""

from __future__ import annotations

import enum


class ChannelType(str, enum.Enum):
    INSTAGRAM = "instagram"
    SPOTIFY = "spotify"
    YOUTUBE = "youtube"
    SOUNDCLOUD = "soundcloud"
    DISCORD = "discord"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    IMESSAGE = "imessage"
    EMAIL = "email"
    TELEGRAM = "telegram"
    OTHER = "other"

    @property
    def label(self) -> str:
        return CHANNEL_LABELS[self]


CHANNEL_LABELS: dict[ChannelType, str] = {
    ChannelType.INSTAGRAM: "Instagram",
    ChannelType.SPOTIFY: "Spotify",
    ChannelType.YOUTUBE: "YouTube",
    ChannelType.SOUNDCLOUD: "SoundCloud",
    ChannelType.DISCORD: "Discord",
    ChannelType.PHONE: "Телефон",
    ChannelType.WHATSAPP: "WhatsApp",
    ChannelType.IMESSAGE: "iMessage",
    ChannelType.EMAIL: "Email",
    ChannelType.TELEGRAM: "Telegram",
    ChannelType.OTHER: "Другое",
}

# Каналы, значение которых нормализуется как телефон.
PHONE_CHANNELS = {ChannelType.PHONE, ChannelType.WHATSAPP, ChannelType.IMESSAGE}


class ContactSource(str, enum.Enum):
    MANUAL = "manual"
    INSTAGRAM = "instagram"
    SPOTIFY = "spotify"
    IMPORT = "import"
    REFERRAL = "referral"
    CAMPAIGN = "campaign"
    OTHER = "other"


SOURCE_LABELS: dict[ContactSource, str] = {
    ContactSource.MANUAL: "Вручную",
    ContactSource.INSTAGRAM: "Instagram",
    ContactSource.SPOTIFY: "Spotify",
    ContactSource.IMPORT: "Импорт",
    ContactSource.REFERRAL: "Рекомендация",
    ContactSource.CAMPAIGN: "Кампания",
    ContactSource.OTHER: "Другое",
}


class DealStage(str, enum.Enum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"


DEAL_STAGE_LABELS: dict[DealStage, str] = {
    DealStage.OPEN: "В работе",
    DealStage.WON: "Оплачено",
    DealStage.LOST: "Отказ",
}


class Direction(str, enum.Enum):
    IN = "in"
    OUT = "out"


class NoteAuthor(str, enum.Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class ReminderState(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    CANCELLED = "cancelled"
    MISSED = "missed"


class AuditLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AuditResult(str, enum.Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class TransferDirection(str, enum.Enum):
    IMPORT = "import"
    EXPORT = "export"


class TransferFormat(str, enum.Enum):
    CSV = "csv"
    XLSX = "xlsx"
    TXT = "txt"


class TransferState(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
