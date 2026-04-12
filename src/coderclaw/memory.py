from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path


class MemoryStore:
    def __init__(self, memory_file: Path, daily_memory_dir: Path) -> None:
        self._memory_file = memory_file
        self._daily_memory_dir = daily_memory_dir

    def load_context(self) -> str:
        parts: list[str] = []

        if self._memory_file.exists():
            memory_text = self._memory_file.read_text(encoding="utf-8").strip()
            if memory_text:
                parts.append(f"Long-term memory from {self._memory_file.name}:\n{memory_text}")

        for day in (date.today() - timedelta(days=1), date.today()):
            day_file = self._daily_memory_dir / f"{day.isoformat()}.md"
            if not day_file.exists():
                continue
            day_text = day_file.read_text(encoding="utf-8").strip()
            if day_text:
                parts.append(f"Daily memory from {day_file.relative_to(self._daily_memory_dir.parent)}:\n{day_text}")

        return "\n\n".join(parts)

    def describe_update_policy(self) -> str:
        return (
            "Persist durable facts, stable preferences, and long-term design decisions to .coder_home/MEMORY.md. "
            "Persist short-horizon notes and daily context to memory/daily/YYYY-MM-DD.md. "
            "If the user says to remember something, update the appropriate file as part of the task. "
            "Do not rely on hidden memory; Markdown files are the source of truth."
        )
