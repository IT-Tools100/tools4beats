"""Точка входа приложения и настройка логирования."""

from __future__ import annotations

import logging
import logging.handlers
import sys

from PySide6.QtWidgets import QApplication

from verse.config import Settings, load_settings
from verse.context import AppContext
from verse.runtime import Runtime
from verse.security.redaction import RedactionFilter
from verse.ui.formatting import mask_dsn
from verse.ui.main_window import MainWindow
from verse.ui.theme import STYLESHEET


def setup_logging(settings: Settings) -> None:
    settings.ensure_dirs()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S"
    )
    redaction = RedactionFilter()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.addFilter(redaction)
    root.addHandler(console)

    file_handler = logging.handlers.RotatingFileHandler(
        settings.logs_dir / "verse.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    )
    file_handler.addFilter(redaction)
    root.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def main() -> int:
    settings = load_settings()
    setup_logging(settings)

    app = QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    app.setApplicationDisplayName(settings.app_name)
    app.setStyleSheet(STYLESHEET)

    context = AppContext.build(settings)
    runtime = Runtime()
    runtime.start()
    logging.getLogger(__name__).info(
        "Project Verse %s запущен; БД: %s", __import__("verse").__version__,
        mask_dsn(settings.database_url),
    )

    window = MainWindow(context, runtime)
    window.show()

    exit_code = app.exec()

    try:
        runtime.submit(context.db.disposed).result(timeout=5)
    except Exception:  # noqa: BLE001 — при завершении не роняем приложение
        logging.getLogger(__name__).warning("не удалось корректно закрыть пул БД")
    runtime.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
