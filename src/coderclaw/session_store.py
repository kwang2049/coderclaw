from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from coderclaw.models import AgentResult, InboundMessage


class SessionStore:
    def __init__(self, sessions_dir: Path) -> None:
        self._sessions_dir = sessions_dir

    def record_success(self, message: InboundMessage, prompt: str, result: AgentResult) -> Path:
        payload = {
            "recorded_at": datetime.now(UTC).isoformat(),
            "status": "success",
            "message": _message_to_json(message),
            "prompt": prompt,
            "output_text": result.output_text,
            "raw_output": result.raw_output,
            "metadata": _metadata_to_json(result.metadata),
        }
        return self._append_record(message.session_key, payload)

    def record_failure(self, message: InboundMessage, prompt: str, error: str) -> Path:
        payload = {
            "recorded_at": datetime.now(UTC).isoformat(),
            "status": "failure",
            "message": _message_to_json(message),
            "prompt": prompt,
            "error": error,
        }
        return self._append_record(message.session_key, payload)

    def _append_record(self, session_key: str, payload: dict[str, object]) -> Path:
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        session_file = self._sessions_dir / f"{_slugify(session_key)}.jsonl"
        with session_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return session_file


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return slug or "session"


def _message_to_json(message: InboundMessage) -> dict[str, object]:
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


def _metadata_to_json(metadata: object) -> dict[str, object] | None:
    if metadata is None:
        return None
    return {
        "runtime_name": metadata.runtime_name,
        "command": metadata.command,
        "cwd": metadata.cwd,
        "started_at": metadata.started_at,
        "completed_at": metadata.completed_at,
        "duration_seconds": metadata.duration_seconds,
        "exit_code": metadata.exit_code,
    }
