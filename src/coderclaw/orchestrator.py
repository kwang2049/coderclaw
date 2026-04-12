from __future__ import annotations

import logging

from coderclaw.channels.slack import SlackAdapter
from coderclaw.memory import MemoryStore
from coderclaw.models import ChannelName, InboundMessage
from coderclaw.policy import SelfImprovementPolicy
from coderclaw.runtimes.base import AgentRuntime
from coderclaw.watchdog import Watchdog


class SessionOrchestrator:
    def __init__(
        self,
        runtime: AgentRuntime,
        memory_store: MemoryStore,
        policy: SelfImprovementPolicy,
        slack: SlackAdapter,
        watchdog: Watchdog,
    ) -> None:
        self._runtime = runtime
        self._memory_store = memory_store
        self._policy = policy
        self._slack = slack
        self._watchdog = watchdog
        self._logger = logging.getLogger(__name__)

    def handle_message(self, message: InboundMessage) -> None:
        self._watchdog.record_heartbeat("orchestrator")
        self._logger.info("handling message id=%s session=%s", message.message_id, message.session_key)
        prompt = self._build_prompt(message)
        try:
            result = self._runtime.execute(prompt)
        except Exception as exc:  # pragma: no cover - defensive entry point
            self._logger.exception("runtime execution failed")
            self._reply(message, f"CoderClaw failed to execute the request: {exc}")
            return

        self._reply(message, result.output_text)

    def _build_prompt(self, message: InboundMessage) -> str:
        memory_context = self._memory_store.load_context()
        memory_update_policy = self._memory_store.describe_update_policy()
        policy_guidance = self._policy.guidance()
        return "\n\n".join(
            part
            for part in [
                "You are running inside CoderClaw through a Slack-driven local orchestration layer.",
                f"Persistent memory:\n{memory_context}" if memory_context else "",
                f"Memory update policy:\n{memory_update_policy}",
                f"Policy guidance:\n{policy_guidance}",
                f"User request from {message.channel.value}:\n{message.text}",
            ]
            if part
        )

    def _reply(self, message: InboundMessage, text: str) -> None:
        if message.reply_target.channel is ChannelName.SLACK:
            self._slack.post_message(
                channel_id=message.reply_target.channel_id,
                thread_ts=message.reply_target.thread_ts,
                text=text,
            )
