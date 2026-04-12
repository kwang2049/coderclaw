from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from coderclaw.models import ChannelName, InboundMessage, ReplyTarget


MENTION_RE = re.compile(r"<@[^>]+>")


@dataclass(frozen=True)
class SlackEventEnvelope:
    raw_body: bytes
    headers: dict[str, str]
    payload: dict[str, object]


class SlackAdapter:
    def __init__(self, bot_token: str | None, signing_secret: str | None) -> None:
        self._bot_token = bot_token
        self._signing_secret = signing_secret
        self._logger = logging.getLogger(__name__)

    def verify_signature(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        if not self._signing_secret:
            self._logger.warning("SLACK_SIGNING_SECRET is not set; skipping Slack signature verification")
            return True

        timestamp = headers.get("x-slack-request-timestamp", "")
        signature = headers.get("x-slack-signature", "")
        if not timestamp or not signature:
            return False
        try:
            timestamp_value = int(timestamp)
        except ValueError:
            return False
        if abs(time.time() - timestamp_value) > 60 * 5:
            return False

        base = f"v0:{timestamp_value}:".encode("utf-8") + raw_body
        expected = "v0=" + hmac.new(
            self._signing_secret.encode("utf-8"),
            base,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def decode(self, raw_body: bytes) -> dict[str, object]:
        return json.loads(raw_body.decode("utf-8"))

    def extract_message(self, payload: dict[str, object]) -> InboundMessage | None:
        if payload.get("type") != "event_callback":
            return None

        event = payload.get("event")
        if not isinstance(event, dict):
            return None
        if event.get("type") != "app_mention":
            return None

        text = str(event.get("text", ""))
        normalized_text = MENTION_RE.sub("", text).strip()
        event_ts = str(event.get("ts", ""))
        channel_id = str(event.get("channel", ""))
        user_id = str(event.get("user", "")) or None
        if not normalized_text or not event_ts or not channel_id:
            return None

        self._logger.info("received Slack app_mention event channel=%s ts=%s", channel_id, event_ts)

        return InboundMessage(
            message_id=f"slack:{event_ts}",
            channel=ChannelName.SLACK,
            text=normalized_text,
            user_id=user_id,
            session_key=f"slack:{channel_id}:{event.get('thread_ts', event_ts)}",
            reply_target=ReplyTarget(
                channel=ChannelName.SLACK,
                channel_id=channel_id,
                thread_ts=str(event.get("thread_ts", event_ts)),
                user_id=user_id,
            ),
        )

    def post_message(self, channel_id: str, text: str, thread_ts: str | None = None) -> None:
        if not self._bot_token:
            raise RuntimeError("SLACK_BOT_TOKEN is not set")

        body = {"channel": channel_id, "text": text}
        if thread_ts:
            body["thread_ts"] = thread_ts

        request = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._bot_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Slack API request failed: {exc}") from exc

        if not payload.get("ok"):
            raise RuntimeError(f"Slack API error: {payload}")

        self._logger.info("posted Slack reply channel=%s thread_ts=%s", channel_id, thread_ts)
