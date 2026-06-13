from __future__ import annotations

from typing import Protocol

from coderclaw.models import AgentResult, AgentSessionRequest


class AgentClient(Protocol):
    def execute_session(self, request: AgentSessionRequest) -> AgentResult:
        """Run a thread-scoped coding-agent session request and return the result."""
