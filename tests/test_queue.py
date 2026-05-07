from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coderclaw.models import ChannelName, InboundMessage, ReplyTarget
from coderclaw.queue import DurableMessageQueue


def make_message(message_id: str = "slack:Ev123", session_key: str = "slack:C123:1710000000.000000") -> InboundMessage:
    return InboundMessage(
        message_id=message_id,
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


class DurableMessageQueueTests(unittest.TestCase):
    def test_enqueue_persists_message_to_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "queue.json"
            queue = DurableMessageQueue(state_path)

            queue.put(make_message())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(queue.pending_count(), 1)
            self.assertEqual(state["queued_messages"][0]["message_id"], "slack:Ev123")
            self.assertEqual(state["queued_messages"][0]["reply_target"]["channel"], "slack")

    def test_dequeue_records_active_session_then_removes_completed_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "queue.json"
            queue = DurableMessageQueue(state_path)
            message = make_message()
            observed_active_sessions: list[dict[str, object]] = []

            queue.put(message)

            def handler(_: InboundMessage) -> None:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                observed_active_sessions.append(state["active_sessions"])

            processed = queue.process_next(handler)

            final_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertTrue(processed)
            self.assertEqual(queue.pending_count(), 0)
            self.assertEqual(queue.active_count(), 0)
            self.assertIn(message.session_key, observed_active_sessions[0])
            self.assertEqual(final_state["queued_messages"], [])
            self.assertEqual(final_state["active_sessions"], {})

    def test_restart_recovers_queued_and_active_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "queue.json"
            queued_message = make_message("slack:Queued", "slack:C123:queued")
            active_message = make_message("slack:Active", "slack:C123:active")
            state_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "queued_messages": [_message_payload(queued_message)],
                        "active_sessions": {
                            active_message.session_key: {
                                "message": _message_payload(active_message),
                                "started_at": "2026-04-28T00:00:00+00:00",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            queue = DurableMessageQueue(state_path)
            processed: list[str] = []

            queue.process_next(lambda message: processed.append(message.message_id))
            queue.process_next(lambda message: processed.append(message.message_id))

            self.assertEqual(processed, ["slack:Active", "slack:Queued"])
            self.assertEqual(queue.pending_count(), 0)

    def test_corrupted_persistence_is_quarantined_and_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "queue.json"
            state_path.write_text("{not json", encoding="utf-8")

            with self.assertLogs("coderclaw.queue", level="WARNING"):
                queue = DurableMessageQueue(state_path)

            self.assertEqual(queue.pending_count(), 0)
            self.assertFalse(state_path.exists())
            corrupt_files = list(Path(tmpdir).glob("queue.json.corrupt-*"))
            self.assertEqual(len(corrupt_files), 1)


def _message_payload(message: InboundMessage) -> dict[str, object]:
    return {
        "message_id": message.message_id,
        "channel": message.channel.value,
        "text": message.text,
        "user_id": message.user_id,
        "session_key": message.session_key,
        "reply_target": {
            "channel": message.reply_target.channel.value,
            "channel_id": message.reply_target.channel_id,
            "message_ts": message.reply_target.message_ts,
            "thread_ts": message.reply_target.thread_ts,
            "user_id": message.reply_target.user_id,
        },
    }


if __name__ == "__main__":
    unittest.main()
