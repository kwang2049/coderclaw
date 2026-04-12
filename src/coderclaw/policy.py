from __future__ import annotations


class SelfImprovementPolicy:
    def guidance(self) -> str:
        return (
            "Prefer updating AGENTS.md or persistent memory before broader code mutation. "
            "Keep changes auditable, bounded, and aligned with the local-first architecture."
        )

