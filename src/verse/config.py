"""Конфигурация приложения (переменные окружения и .env)."""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_name: str = "Project Verse"

    database_url: str = "postgresql+psycopg://verse:verse@127.0.0.1:5433/verse"
    test_database_url: str = "postgresql+psycopg://verse:verse@127.0.0.1:5433/verse_test"

    data_dir: Path = Path("~/Library/Application Support/ProjectVerse")
    log_level: str = "INFO"

    @field_validator("data_dir", mode="after")
    @classmethod
    def _expand(cls, value: Path) -> Path:
        return Path(value).expanduser()

    # --- производные пути -------------------------------------------------
    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def ensure_dirs(self) -> Path:
        """Создаёт каталоги данных.

        Если системный путь недоступен (песочница, ограниченные права),
        используется локальный `./data` — приложение не падает на старте.
        """
        for candidate in (self.data_dir, Path.cwd() / "data"):
            try:
                for path in (candidate, candidate / "exports", candidate / "backups",
                             candidate / "logs"):
                    path.mkdir(parents=True, exist_ok=True)
            except OSError:
                continue
            self.data_dir = candidate
            return candidate
        raise OSError("Не удалось создать каталог данных приложения")


def load_settings() -> Settings:
    return Settings()
