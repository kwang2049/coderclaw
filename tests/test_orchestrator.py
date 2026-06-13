from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coderclaw.models import (
    AgentResult,
    AgentSessionRequest,
    ChannelName,
    ContextMessage,
    InboundMessage,
    ReplyTarget,
)
from coderclaw.orchestrator import SessionOrchestrator
from coderclaw.session_store import SessionStore


class FakeAgent:
    def __init__(self) -> None:
        self.requests: list[AgentSessionRequest] = []

    def execute_session(self, request: AgentSessionRequest) -> AgentResult:
        self.requests.append(request)
        return AgentResult(output_text="done", raw_output="done")


class FakeSlack:
    def __init__(self) -> None:
        self.reactions: list[tuple[str, str]] = []
        self.replies: list[tuple[str, str | None, str]] = []

    def add_reaction(self, channel_id: str, timestamp: str, emoji_name: str) -> None:
        self.reactions.append(("add", emoji_name))

    def remove_reaction(self, channel_id: str, timestamp: str, emoji_name: str) -> None:
        self.reactions.append(("remove", emoji_name))

    def post_message(self, channel_id: str, text: str, thread_ts: str | None = None) -> None:
        self.replies.append((channel_id, thread_ts, text))


class FakeWatchdog:
    def __init__(self) -> None:
        self.components: list[str] = []

    def record_heartbeat(self, component: str) -> None:
        self.components.append(component)


def make_message() -> InboundMessage:
    return InboundMessage(
        message_id="slack:Ev123",
        channel=ChannelName.SLACK,
        text="run tests",
        user_id="U222",
        session_key="slack:C123:1710000000.000000",
        reply_target=ReplyTarget(
            channel=ChannelName.SLACK,
            channel_id="C123",
            message_ts="1710000000.000100",
            thread_ts="1710000000.000000",
            user_id="U222",
        ),
        context_messages=(
            ContextMessage(
                channel=ChannelName.SLACK,
                message_ts="1710000000.000000",
                thread_ts="1710000000.000000",
                user_id="U111",
                text="root request",
            ),
            ContextMessage(
                channel=ChannelName.SLACK,
                message_ts="1710000000.000100",
                thread_ts="1710000000.000000",
                user_id="U222",
                text="run tests",
            ),
        ),
    )


class SessionOrchestratorTests(unittest.TestCase):
    def test_sends_thread_scoped_agent_session_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = FakeAgent()
            slack = FakeSlack()
            orchestrator = SessionOrchestrator(
                agent=agent,
                session_store=SessionStore(Path(tmpdir)),
                slack=slack,
                watchdog=FakeWatchdog(),
            )

            orchestrator.handle_message(make_message())

            self.assertEqual(len(agent.requests), 1)
            request = agent.requests[0]
            self.assertEqual(request.session_key, "slack:C123:1710000000.000000")
            self.assertEqual(request.latest_user_text, "run tests")
            self.assertEqual([item.text for item in request.messages], ["root request", "run tests"])
            self.assertEqual(slack.replies, [("C123", "1710000000.000000", "done")])


if __name__ == "__main__":
    unittest.main()
