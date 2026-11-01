"""Мост между asyncio-рантаймом и GUI-потоком.

Правило: колбэки выполняются строго в потоке Qt. Реализация — сигнал с
queued-соединением: `Future.add_done_callback` вызывается в потоке рантайма,
а `_deliver` уже в GUI-потоке.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal, Slot

log = logging.getLogger(__name__)


class AsyncRunner(QObject):
    _deliver = Signal(object, object, object, object)  # on_success, on_error, payload, error

    def __init__(self, runtime, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._runtime = runtime
        self._closed = False
        self._deliver.connect(self._dispatch, Qt.ConnectionType.QueuedConnection)

    def close(self) -> None:
        """Окно закрывается: результаты «в полёте» игнорируются."""
        self._closed = True

    def run(
        self,
        factory: Callable[[], Any],
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
    ) -> None:
        try:
            future = self._runtime.submit(factory)
        except BaseException as exc:  # noqa: BLE001
            self._dispatch(on_success, on_error, None, exc)
            return

        def _callback(done) -> None:
            try:
                payload = done.result()
            except BaseException as exc:  # noqa: BLE001
                self._deliver.emit(on_success, on_error, None, exc)
            else:
                self._deliver.emit(on_success, on_error, payload, None)

        future.add_done_callback(_callback)

    @Slot(object, object, object, object)
    def _dispatch(self, on_success, on_error, payload, error) -> None:
        if self._closed:
            return
        if error is not None:
            log.warning("async call failed: %s", error)
            if on_error is not None:
                on_error(error)
            return
        if on_success is not None:
            on_success(payload)


class InertRunner(QObject):
    """Заглушка для UI-тестов: выполняет фабрики синхронно, без сети и БД."""

    def __init__(self, result: Any = None) -> None:
        super().__init__()
        self._result = result

    def run(self, factory, on_success=None, on_error=None) -> None:  # noqa: ANN001
        if on_success is not None:
            try:
                payload = self._result
            except Exception:  # pragma: no cover
                payload = None
            on_success(payload)
