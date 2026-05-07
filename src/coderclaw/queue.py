from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from coderclaw.models import ChannelName, InboundMessage, ReplyTarget

MessageHandler = Callable[[InboundMessage], None]


class DurableMessageQueue:
    STATE_VERSION = 1

    def __init__(self, state_path: Path) -> None:
        self._state_path = state_path
        self._queue: queue.Queue[InboundMessage] = queue.Queue()
        self._queued_messages: list[InboundMessage] = []
        self._active_sessions: dict[str, ActiveSession] = {}
        self._message_ids: set[str] = set()
        self._lock = threading.RLock()
        self._worker: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._logger = logging.getLogger(__name__)
        self._load_state()

    def put(self, message: InboundMessage) -> None:
        with self._lock:
            if message.message_id in self._message_ids:
                self._logger.info("ignored duplicate queued message id=%s", message.message_id)
                return
            self._queued_messages.append(message)
            self._message_ids.add(message.message_id)
            self._write_state()
        self._queue.put(message)

    def start(self, handler: MessageHandler) -> None:
        if self._worker and self._worker.is_alive():
            return

        def run() -> None:
            self._logger.info("message queue worker started")
            while not self._stop_event.is_set():
                try:
                    message = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    self._logger.info("processing queued message id=%s", message.message_id)
                    self._mark_active(message)
                    handler(message)
                except Exception:  # pragma: no cover - defensive worker guard
                    self._logger.exception("unhandled exception while processing message id=%s", message.message_id)
                finally:
                    self._mark_complete(message)
                    self._queue.task_done()

        self._worker = threading.Thread(target=run, name="coderclaw-queue", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._worker:
            self._worker.join(timeout=2)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._queued_messages)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active_sessions)

    def process_next(self, handler: MessageHandler) -> bool:
        try:
            message = self._queue.get_nowait()
        except queue.Empty:
            return False

        try:
            self._mark_active(message)
            handler(message)
        finally:
            self._mark_complete(message)
            self._queue.task_done()
        return True

    def _mark_active(self, message: InboundMessage) -> None:
        with self._lock:
            self._queued_messages = [
                queued for queued in self._queued_messages if queued.message_id != message.message_id
            ]
            self._active_sessions[message.session_key] = ActiveSession(
                message=message,
                started_at=datetime.now(UTC).isoformat(),
            )
            self._write_state()

    def _mark_complete(self, message: InboundMessage) -> None:
        with self._lock:
            active = self._active_sessions.get(message.session_key)
            if active and active.message.message_id == message.message_id:
                del self._active_sessions[message.session_key]
            self._message_ids.discard(message.message_id)
            self._write_state()

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return

        try:
            raw_state = json.loads(self._state_path.read_text(encoding="utf-8"))
            queued_messages: list[InboundMessage] = []
            active_sessions = raw_state.get("active_sessions", {})
            if isinstance(active_sessions, dict):
                for raw_active in active_sessions.values():
                    if not isinstance(raw_active, dict):
                        continue
                    raw_message = raw_active.get("message")
                    if isinstance(raw_message, dict):
                        queued_messages.append(_message_from_json(raw_message))
            queued_messages.extend(
                _message_from_json(raw_message)
                for raw_message in raw_state.get("queued_messages", [])
                if isinstance(raw_message, dict)
            )
        except Exception as exc:
            self._logger.warning("failed to load queue persistence from %s: %s", self._state_path, exc)
            self._quarantine_corrupt_state()
            return

        for message in queued_messages:
            if message.message_id in self._message_ids:
                continue
            self._queued_messages.append(message)
            self._message_ids.add(message.message_id)
            self._queue.put(message)

        if queued_messages:
            self._logger.info("restored %s unfinished queued messages", len(self._queued_messages))
            self._write_state()

    def _quarantine_corrupt_state(self) -> None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        corrupt_path = self._state_path.with_name(f"{self._state_path.name}.corrupt-{timestamp}")
        try:
            self._state_path.replace(corrupt_path)
            self._logger.warning("moved corrupt queue persistence to %s", corrupt_path)
        except OSError as exc:
            self._logger.warning("failed to quarantine corrupt queue persistence: %s", exc)

    def _write_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.STATE_VERSION,
            "queued_messages": [_message_to_json(message) for message in self._queued_messages],
            "active_sessions": {
                session_key: {
                    "message": _message_to_json(active.message),
                    "started_at": active.started_at,
                }
                for session_key, active in self._active_sessions.items()
            },
        }
        temporary_path = self._state_path.with_suffix(f"{self._state_path.suffix}.tmp")
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temporary_path.replace(self._state_path)


@dataclass(frozen=True)
class ActiveSession:
    message: InboundMessage
    started_at: str


def _message_to_json(message: InboundMessage) -> dict[str, Any]:
    payload = asdict(message)
    payload["channel"] = message.channel.value
    payload["reply_target"]["channel"] = message.reply_target.channel.value
    return payload


def _message_from_json(payload: dict[str, Any]) -> InboundMessage:
    reply_target = payload["reply_target"]
    return InboundMessage(
        message_id=str(payload["message_id"]),
        channel=ChannelName(str(payload["channel"])),
        text=str(payload["text"]),
        user_id=payload.get("user_id"),
        session_key=str(payload["session_key"]),
        reply_target=ReplyTarget(
            channel=ChannelName(str(reply_target["channel"])),
            channel_id=str(reply_target["channel_id"]),
            message_ts=str(reply_target["message_ts"]),
            thread_ts=reply_target.get("thread_ts"),
            user_id=reply_target.get("user_id"),
        ),
    )


InMemoryMessageQueue = DurableMessageQueue
