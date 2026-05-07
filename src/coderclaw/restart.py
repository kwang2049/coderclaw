from __future__ import annotations

import fcntl
from pathlib import Path
from typing import Callable


class RestartController:
    def __init__(self, lock_file: Path) -> None:
        self._lock_file = lock_file
        self._requested = False
        self._intake_stopped = False

    def request_restart(self) -> None:
        self._requested = True

    def is_requested(self) -> bool:
        return self._requested

    def prepare_for_restart(self, stop_intake: Callable[[], None]) -> None:
        if not self._requested or self._intake_stopped:
            return
        stop_intake()
        self._intake_stopped = True

    def perform_restart(
        self,
        stop_runtime: Callable[[], None],
        reexec: Callable[[], None],
    ) -> None:
        self._lock_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_file.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            stop_runtime()
            reexec()
