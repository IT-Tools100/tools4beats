"""Контейнер зависимостей приложения (composition root передаёт его во views)."""

from __future__ import annotations

from dataclasses import dataclass, field

from verse.config import Settings
from verse.db.session import Database
from verse.services.contacts import ContactService
from verse.services.deals import DealService


@dataclass
class AppContext:
    settings: Settings
    db: Database
    contacts: ContactService
    deals: DealService
    status_groups: list = field(default_factory=list)

    @classmethod
    def build(cls, settings: Settings) -> "AppContext":
        db = Database(settings.database_url)
        return cls(
            settings=settings,
            db=db,
            contacts=ContactService(db),
            deals=DealService(db),
        )
