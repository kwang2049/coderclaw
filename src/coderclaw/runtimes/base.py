from __future__ import annotations

from typing import Protocol

from coderclaw.models import AgentResult


class AgentRuntime(Protocol):
    def execute(self, prompt: str) -> AgentResult:
        """Run the prompt through a coding agent and return the result."""

