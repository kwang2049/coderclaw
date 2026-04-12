from __future__ import annotations

from pathlib import Path


class MemoryStore:
    def __init__(self, memory_file: Path) -> None:
        self._memory_file = memory_file

    def load_context(self) -> str:
        if not self._memory_file.exists():
            return ""
        return self._memory_file.read_text(encoding="utf-8").strip()

