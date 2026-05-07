from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coderclaw.models import AgentResult, ChannelName, InboundMessage, ReplyTarget, RuntimeExecutionMetadata
from coderclaw.session_store import SessionStore


def make_message(session_key: str = "slack:C123:1710000000.000000") -> InboundMessage:
    return InboundMessage(
        message_id="slack:Ev123",
        channel=ChannelName.SLACK,
        text="run tests",
        user_id="U123",
        session_key=session_key,
        reply_target=ReplyTarget(
            channel=ChannelName.SLACK,
            channel_id="C123",
            message_ts="1710000000.000100",
            thread_ts="1710000000.000000",
            user_id="U123",
        ),
    )


class SessionStoreTests(unittest.TestCase):
    def test_records_success_to_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir))
            result = AgentResult(
                output_text="done",
                raw_output="done",
                metadata=RuntimeExecutionMetadata(
                    runtime_name="codex",
                    command=["codex", "exec"],
                    cwd="/tmp/repo",
                    started_at="2026-05-07T00:00:00+00:00",
                    completed_at="2026-05-07T00:00:01+00:00",
                    duration_seconds=1.0,
                    exit_code=0,
                ),
            )

            session_file = store.record_success(make_message(), "prompt", result)

            records = session_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 1)
            payload = json.loads(records[0])
            self.assertEqual(payload["status"], "success")
            self.assertEqual(payload["message"]["session_key"], "slack:C123:1710000000.000000")
            self.assertEqual(payload["output_text"], "done")
            self.assertEqual(payload["metadata"]["runtime_name"], "codex")

    def test_records_failure_to_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir))

            session_file = store.record_failure(make_message("slack:D123:1"), "prompt", "boom")

            records = session_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(records), 1)
            payload = json.loads(records[0])
            self.assertEqual(payload["status"], "failure")
            self.assertEqual(payload["error"], "boom")


if __name__ == "__main__":
    unittest.main()
