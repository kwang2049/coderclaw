from __future__ import annotations

import unittest
from types import SimpleNamespace

from coderclaw.channels.slack import SlackAdapter
from coderclaw.models import ChannelName


class FakeSocketClient:
    def __init__(self) -> None:
        self.responses: list[object] = []

    def send_socket_mode_response(self, response: object) -> None:
        self.responses.append(response)


class SlackAdapterTests(unittest.TestCase):
    def test_extracts_app_mention_with_event_id_and_thread_session(self) -> None:
        adapter = SlackAdapter(bot_token=None, app_token=None)

        message = adapter.extract_message(
            {
                "event_id": "Ev123",
                "event": {
                    "type": "app_mention",
                    "channel": "C123",
                    "ts": "1710000000.000100",
                    "thread_ts": "1710000000.000000",
                    "user": "U123",
                    "text": "<@U999> inspect the repo",
                },
            }
        )

        self.assertIsNotNone(message)
        assert message is not None
        self.assertEqual(message.message_id, "slack:Ev123")
        self.assertEqual(message.channel, ChannelName.SLACK)
        self.assertEqual(message.text, "inspect the repo")
        self.assertEqual(message.session_key, "slack:C123:1710000000.000000")
        self.assertEqual(message.reply_target.thread_ts, "1710000000.000000")

    def test_extracts_direct_message_without_mention(self) -> None:
        adapter = SlackAdapter(bot_token=None, app_token=None)

        message = adapter.extract_message(
            {
                "event_id": "Ev456",
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "channel": "D123",
                    "ts": "1710000001.000100",
                    "user": "U123",
                    "text": "status please",
                },
            }
        )

        self.assertIsNotNone(message)
        assert message is not None
        self.assertEqual(message.message_id, "slack:Ev456")
        self.assertEqual(message.text, "status please")
        self.assertEqual(message.session_key, "slack:D123:1710000001.000100")

    def test_ignores_bot_messages(self) -> None:
        adapter = SlackAdapter(bot_token=None, app_token=None)

        message = adapter.extract_message(
            {
                "event_id": "EvBot",
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "channel": "D123",
                    "ts": "1710000002.000100",
                    "bot_id": "B123",
                    "text": "loop",
                },
            }
        )

        self.assertIsNone(message)

    def test_socket_request_acks_and_deduplicates_events(self) -> None:
        adapter = SlackAdapter(bot_token=None, app_token=None)
        queued: list[str] = []
        adapter.start_socket_mode(lambda message: queued.append(message.message_id))
        client = FakeSocketClient()
        request = SimpleNamespace(
            envelope_id="env-1",
            type="events_api",
            payload={
                "event_id": "EvDuplicate",
                "event": {
                    "type": "app_mention",
                    "channel": "C123",
                    "ts": "1710000003.000100",
                    "user": "U123",
                    "text": "<@U999> run audit",
                },
            },
        )

        adapter._handle_socket_request(client, request)
        adapter._handle_socket_request(client, request)

        self.assertEqual(queued, ["slack:EvDuplicate"])
        self.assertEqual(len(client.responses), 2)


if __name__ == "__main__":
    unittest.main()
