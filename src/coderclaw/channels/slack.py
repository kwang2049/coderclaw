from __future__ import annotations

import logging
import re
import threading
from collections import deque
from collections.abc import Callable

from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web import WebClient

from coderclaw.models import ChannelName, ContextMessage, InboundMessage, ReplyTarget


MENTION_RE = re.compile(r"<@[^>]+>")


class SlackAdapter:
    def __init__(self, bot_token: str | None, app_token: str | None, dedupe_cache_size: int = 256) -> None:
        self._bot_token = bot_token
        self._app_token = app_token
        self._logger = logging.getLogger(__name__)
        self._web_client = WebClient(token=bot_token) if bot_token else None
        self._socket_client: SocketModeClient | None = None
        self._message_handler: Callable[[InboundMessage], None] | None = None
        self._seen_message_ids: set[str] = set()
        self._seen_message_order: deque[str] = deque(maxlen=dedupe_cache_size)
        self._seen_message_lock = threading.Lock()

    def start_socket_mode(self, on_message: Callable[[InboundMessage], None]) -> None:
        self._message_handler = on_message
        if not self._bot_token or not self._app_token:
            self._logger.warning("Slack Socket Mode is disabled because SLACK_BOT_TOKEN or SLACK_APP_TOKEN is missing")
            return

        if self._socket_client:
            return

        self._socket_client = SocketModeClient(
            app_token=self._app_token,
            web_client=self._web_client,
        )
        self._socket_client.socket_mode_request_listeners.append(self._handle_socket_request)
        self._socket_client.connect()
        self._logger.info("Slack Socket Mode connected")

    def stop_socket_mode(self) -> None:
        if not self._socket_client:
            return
        self._socket_client.disconnect()
        self._socket_client = None

    def is_socket_mode_connected(self) -> bool:
        return self._socket_client is not None

    def extract_message(self, payload: dict[str, object]) -> InboundMessage | None:
        event = payload.get("event")
        if not isinstance(event, dict):
            return None

        event_type = event.get("type")
        event_id = str(payload.get("event_id", ""))
        channel_id = str(event.get("channel", ""))
        event_ts = str(event.get("ts", ""))
        user_id = str(event.get("user", "")) or None
        thread_ts = str(event.get("thread_ts", event_ts))
        channel_type = str(event.get("channel_type", ""))
        subtype = event.get("subtype")
        bot_id = event.get("bot_id")

        if bot_id:
            return None

        normalized_text: str | None = None
        if event_type == "app_mention":
            text = str(event.get("text", ""))
            normalized_text = MENTION_RE.sub("", text).strip()
            self._logger.info("received Slack app_mention event channel=%s ts=%s", channel_id, event_ts)
        elif event_type == "message" and channel_type == "im" and subtype is None:
            normalized_text = str(event.get("text", "")).strip()
            self._logger.info("received Slack direct message channel=%s ts=%s", channel_id, event_ts)
        else:
            return None

        if not normalized_text or not event_ts or not channel_id:
            return None

        message_id = f"slack:{event_id}" if event_id else f"slack:{channel_id}:{event_ts}"
        fallback_context = ContextMessage(
            channel=ChannelName.SLACK,
            message_ts=event_ts,
            thread_ts=thread_ts,
            user_id=user_id,
            text=normalized_text,
        )
        context_messages = tuple(
            self.fetch_thread_context_messages(
                channel_id=channel_id,
                event_ts=event_ts,
                thread_ts=thread_ts,
                fallback_context=fallback_context,
                limit=1000,
            )
        )
        return InboundMessage(
            message_id=message_id,
            channel=ChannelName.SLACK,
            text=normalized_text,
            user_id=user_id,
            session_key=f"slack:{channel_id}:{thread_ts}",
            reply_target=ReplyTarget(
                channel=ChannelName.SLACK,
                channel_id=channel_id,
                message_ts=event_ts,
                thread_ts=thread_ts,
                user_id=user_id,
            ),
            context_messages=context_messages,
        )

    def add_reaction(self, channel_id: str, timestamp: str, emoji_name: str) -> None:
        self._require_web_client().reactions_add(channel=channel_id, timestamp=timestamp, name=emoji_name)
        self._logger.info("added Slack reaction channel=%s ts=%s emoji=%s", channel_id, timestamp, emoji_name)

    def remove_reaction(self, channel_id: str, timestamp: str, emoji_name: str) -> None:
        try:
            self._require_web_client().reactions_remove(channel=channel_id, timestamp=timestamp, name=emoji_name)
        except SlackApiError as exc:
            if exc.response.get("error") != "no_reaction":
                raise
        self._logger.info("removed Slack reaction channel=%s ts=%s emoji=%s", channel_id, timestamp, emoji_name)

    def post_message(self, channel_id: str, text: str, thread_ts: str | None = None) -> None:
        body: dict[str, object] = {"channel": channel_id, "text": text}
        if thread_ts:
            body["thread_ts"] = thread_ts

        self._require_web_client().chat_postMessage(**body)
        self._logger.info("posted Slack reply channel=%s thread_ts=%s", channel_id, thread_ts)

    def fetch_thread_context_messages(
        self,
        channel_id: str,
        event_ts: str,
        thread_ts: str,
        fallback_context: ContextMessage,
        limit: int,
    ) -> list[ContextMessage]:
        if not self._web_client:
            return [fallback_context]

        try:
            replies = self._require_web_client().conversations_replies(channel=channel_id, ts=thread_ts, limit=limit)
            reply_messages = replies.get("messages", [])
            if isinstance(reply_messages, list):
                context = _filter_and_trim_context(
                    [_normalize_context_message(raw) for raw in reply_messages],
                    limit,
                    event_ts=event_ts,
                )
                return context or [fallback_context]
        except SlackApiError:
            self._logger.exception("failed to fetch Slack thread context channel=%s thread_ts=%s", channel_id, thread_ts)
        return [fallback_context]

    def _handle_socket_request(self, client: SocketModeClient, request: SocketModeRequest) -> None:
        if request.envelope_id:
            client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))

        if request.type != "events_api":
            self._logger.info("ignored Slack Socket Mode request type=%s", request.type)
            return

        payload = request.payload
        if not isinstance(payload, dict):
            self._logger.info("ignored Slack Socket Mode payload with non-dict body")
            return

        message = self.extract_message(payload)
        if not message:
            event = payload.get("event")
            event_type = event.get("type") if isinstance(event, dict) else None
            self._logger.info("ignored Slack Socket Mode event type=%s", event_type)
            return

        if not self._message_handler:
            self._logger.warning("received Slack message before handler registration")
            return

        if not self._remember_message(message.message_id):
            self._logger.info("ignored duplicate Slack message id=%s", message.message_id)
            return
        self._message_handler(message)
        self._logger.info("queued Slack message id=%s", message.message_id)

    def _require_web_client(self) -> WebClient:
        if not self._web_client:
            raise RuntimeError("SLACK_BOT_TOKEN is not set")
        return self._web_client

    def _remember_message(self, message_id: str) -> bool:
        with self._seen_message_lock:
            if message_id in self._seen_message_ids:
                return False
            if self._seen_message_order.maxlen == 0:
                return True
            if len(self._seen_message_order) == self._seen_message_order.maxlen and self._seen_message_order:
                expired = self._seen_message_order[0]
                self._seen_message_ids.discard(expired)
            self._seen_message_order.append(message_id)
            self._seen_message_ids.add(message_id)
            return True


def _normalize_context_message(raw: object) -> ContextMessage | None:
    if not isinstance(raw, dict):
        return None
    text = str(raw.get("text", "")).strip()
    message_ts = str(raw.get("ts", "")).strip()
    if not text or not message_ts:
        return None
    if raw.get("subtype") in {"message_deleted", "channel_join", "channel_leave"}:
        return None
    thread_ts_raw = raw.get("thread_ts")
    thread_ts = str(thread_ts_raw).strip() if thread_ts_raw else None
    user_id = str(raw.get("user", "")).strip() or None
    return ContextMessage(
        channel=ChannelName.SLACK,
        message_ts=message_ts,
        thread_ts=thread_ts,
        user_id=user_id,
        text=MENTION_RE.sub("", text).strip(),
    )


def _filter_and_trim_context(
    messages: list[ContextMessage | None],
    limit: int,
    event_ts: str | None = None,
) -> list[ContextMessage]:
    deduped: dict[str, ContextMessage] = {}
    for message in messages:
        if message is None:
            continue
        deduped[message.message_ts] = message

    ordered = sorted(deduped.values(), key=lambda item: float(item.message_ts))
    if event_ts:
        ordered = [message for message in ordered if message.message_ts <= event_ts]
    return ordered[-limit:]
