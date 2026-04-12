from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

from coderclaw.models import InboundMessage

MessageHandler = Callable[[InboundMessage], None]


class InMemoryMessageQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue[InboundMessage] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._logger = logging.getLogger(__name__)

    def put(self, message: InboundMessage) -> None:
        self._queue.put(message)

    def start(self, handler: MessageHandler) -> None:
        if self._worker and self._worker.is_alive():
            return

        def run() -> None:
            self._logger.info("message queue worker started")
            while not self._stop_event.is_set():
                try:
                    message = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    self._logger.info("processing queued message id=%s", message.message_id)
                    handler(message)
                except Exception:  # pragma: no cover - defensive worker guard
                    self._logger.exception("unhandled exception while processing message id=%s", message.message_id)
                finally:
                    self._queue.task_done()

        self._worker = threading.Thread(target=run, name="coderclaw-queue", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=2)
