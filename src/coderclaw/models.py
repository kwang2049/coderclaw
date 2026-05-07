from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChannelName(StrEnum):
    SLACK = "slack"


@dataclass(frozen=True)
class ReplyTarget:
    channel: ChannelName
    channel_id: str
    message_ts: str
    thread_ts: str | None
    user_id: str | None


@dataclass(frozen=True)
class ContextMessage:
    channel: ChannelName
    message_ts: str
    thread_ts: str | None
    user_id: str | None
    text: str


@dataclass(frozen=True)
class InboundMessage:
    message_id: str
    channel: ChannelName
    text: str
    user_id: str | None
    session_key: str
    reply_target: ReplyTarget
    context_messages: tuple[ContextMessage, ...] = ()


@dataclass(frozen=True)
class AgentResult:
    output_text: str
    raw_output: str
    metadata: RuntimeExecutionMetadata | None = None


@dataclass(frozen=True)
class RuntimeExecutionMetadata:
    runtime_name: str
    command: list[str]
    cwd: str
    started_at: str
    completed_at: str
    duration_seconds: float
    exit_code: int
