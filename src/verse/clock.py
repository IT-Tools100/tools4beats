"""Часы — единственный источник текущего времени в бизнес-логике.

Нужны для тестируемости планировщика и отчётов: тесты подменяют часы,
а не системное время.
"""

from __future__ import annotations

import datetime as dt
from typing import Protocol


class Clock(Protocol):
    def now(self) -> dt.datetime: ...

    def today(self) -> dt.date: ...


class SystemClock:
    def now(self) -> dt.datetime:
        return dt.datetime.now(tz=dt.UTC)

    def today(self) -> dt.date:
        return self.now().date()


class FixedClock:
    """Часы с фиксированным временем (для тестов)."""

    def __init__(self, moment: dt.datetime) -> None:
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=dt.UTC)
        self._moment = moment

    def now(self) -> dt.datetime:
        return self._moment

    def today(self) -> dt.date:
        return self._moment.date()

    def advance(self, **kwargs: float) -> None:
        self._moment = self._moment + dt.timedelta(**kwargs)


clock: Clock = SystemClock()
