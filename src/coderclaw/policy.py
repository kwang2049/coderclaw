from __future__ import annotations


class SelfImprovementPolicy:
    def guidance(self) -> str:
        return (
            "Prefer updating AGENTS.md or Markdown memory before broader code mutation. "
            "Use .coder_home/MEMORY.md for durable memory and memory/daily/YYYY-MM-DD.md for daily context. "
            "Keep changes auditable, bounded, and aligned with the local-first architecture."
        )
