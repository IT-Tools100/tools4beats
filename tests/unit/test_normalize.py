"""Нормализация каналов."""

from __future__ import annotations

import pytest

from verse.domain.enums import ChannelType
from verse.domain.normalize import normalize_channel_value
from verse.errors import ValidationError


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Test@Example.COM ", "test@example.com"),
        ("dj.beats@mail.ru", "dj.beats@mail.ru"),
    ],
)
def test_email(raw: str, expected: str) -> None:
    assert normalize_channel_value(ChannelType.EMAIL, raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+7 (999) 123-45-67", "+79991234567"),
        ("89991234567", "+79991234567"),
        ("+1 415 555 0100", "+14155550100"),
    ],
)
def test_phone(raw: str, expected: str) -> None:
    assert normalize_channel_value(ChannelType.PHONE, raw) == expected


def test_phone_short_is_invalid() -> None:
    with pytest.raises(ValidationError):
        normalize_channel_value(ChannelType.PHONE, "123")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("@TestArtist", "testartist"),
        ("https://instagram.com/testartist/", "testartist"),
        ("testartist", "testartist"),
    ],
)
def test_instagram(raw: str, expected: str) -> None:
    assert normalize_channel_value(ChannelType.INSTAGRAM, raw) == expected


def test_empty_channel_is_invalid() -> None:
    with pytest.raises(ValidationError):
        normalize_channel_value(ChannelType.EMAIL, "   ")


def test_spotify_url_to_id() -> None:
    value = normalize_channel_value(
        ChannelType.SPOTIFY, "https://open.spotify.com/artist/1vCWHaC5f2uS3yhpwWbIA6"
    )
    assert value == "1vCWHaC5f2uS3yhpwWbIA6"
