from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path


class Watchdog:
    def __init__(
        self,
        watch_paths: list[Path],
        interval_seconds: int,
        stale_seconds: int,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._watch_paths = watch_paths
        self._interval_seconds = interval_seconds
        self._stale_seconds = stale_seconds
        self._on_change = on_change
        self._heartbeats: dict[str, float] = {}
        self._snapshot = self._take_snapshot()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="coderclaw-watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def record_heartbeat(self, component: str) -> None:
        self._heartbeats[component] = time.time()

    def _run(self) -> None:
        self._logger.info("watchdog started")
        while not self._stop_event.is_set():
            self._log_stale_components()
            self._log_file_changes()
            time.sleep(self._interval_seconds)

    def _log_stale_components(self) -> None:
        now = time.time()
        for component, last_seen in self._heartbeats.items():
            age = now - last_seen
            if age > self._stale_seconds:
                self._logger.warning("watchdog detected stale component=%s age=%.1fs", component, age)

    def _log_file_changes(self) -> None:
        current = self._take_snapshot()
        if current != self._snapshot:
            self._logger.info("watchdog detected source or doc changes")
            self._snapshot = current
            if self._on_change:
                self._on_change()

    def _take_snapshot(self) -> dict[str, int]:
        snapshot: dict[str, int] = {}
        for path in self._watch_paths:
            if path.is_file():
                snapshot[str(path)] = int(path.stat().st_mtime_ns)
            elif path.is_dir():
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        snapshot[str(file_path)] = int(file_path.stat().st_mtime_ns)
        return snapshot
