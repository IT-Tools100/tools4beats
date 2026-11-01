"""Рантайм приложения: один asyncio-loop в отдельном потоке.

UI-поток никогда не выполняет I/O. Виджеты вызывают `Runtime.submit(factory)`
и получают `concurrent.futures.Future`; результат доставляется в GUI-поток
через `verse.ui.bridge.AsyncRunner`.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from typing import Any

log = logging.getLogger(__name__)


class Runtime:
    def __init__(self, name: str = "verse-runtime") -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._started = False
        self._stopping = False

    # --- жизненный цикл ---------------------------------------------------
    def start(self) -> None:
        if self._started:
            return
        self._thread.start()
        self._started = True
        # Дожидаемся, пока loop действительно начнёт работать.
        ready = threading.Event()
        self._loop.call_soon_threadsafe(ready.set)
        if not ready.wait(timeout=5):
            raise RuntimeError("Не удалось запустить asyncio-loop приложения")
        log.debug("runtime started")

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            finally:
                self._loop.close()

    def stop(self, timeout: float = 10.0) -> None:
        if not self._started or self._stopping:
            return
        self._stopping = True
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=timeout)
        self._started = False
        log.debug("runtime stopped")

    # --- выполнение -------------------------------------------------------
    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def submit(
        self, factory: Callable[[], Coroutine[Any, Any, Any]]
    ) -> Future[Any]:
        """Выполнить корутину в рантайме.

        `factory` — функция без аргументов, возвращающая корутину. Фабрика
        вызывается уже внутри loop, поэтому исключения при создании корутины
        тоже попадают во Future.
        """
        if not self._started:
            raise RuntimeError("Runtime не запущен")
        if self._loop.is_closed():
            raise RuntimeError("Runtime уже остановлен")

        async def _runner() -> Any:
            return await factory()

        return asyncio.run_coroutine_threadsafe(_runner(), self._loop)

    def run_blocking(self, factory: Callable[[], Coroutine[Any, Any, Any]], timeout: float = 30.0) -> Any:
        """Только для тестов и CLI: дождаться результата из другого потока."""
        return self.submit(factory).result(timeout=timeout)
