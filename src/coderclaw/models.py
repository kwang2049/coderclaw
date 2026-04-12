from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChannelName(StrEnum):
    SLACK = "slack"


@dataclass(frozen=True)
class ReplyTarget:
    channel: ChannelName
    channel_id: str
    thread_ts: str | None
    user_id: str | None


@dataclass(frozen=True)
class InboundMessage:
    message_id: str
    channel: ChannelName
    text: str
    user_id: str | None
    session_key: str
    reply_target: ReplyTarget


@dataclass(frozen=True)
class AgentResult:
    output_text: str
    raw_output: str

