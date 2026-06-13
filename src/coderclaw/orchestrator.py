from __future__ import annotations

import logging

from coderclaw.acp import AgentClient
from coderclaw.channels.slack import SlackAdapter
from coderclaw.models import AgentSessionMessage, AgentSessionRequest, ChannelName, InboundMessage
from coderclaw.session_store import SessionStore
from coderclaw.watchdog import Watchdog


class SessionOrchestrator:
    IN_PROGRESS_EMOJI = "eyes"
    SUCCESS_EMOJI = "white_check_mark"
    FAILURE_EMOJI = "x"

    def __init__(
        self,
        agent: AgentClient,
        session_store: SessionStore,
        slack: SlackAdapter,
        watchdog: Watchdog,
    ) -> None:
        self._agent = agent
        self._session_store = session_store
        self._slack = slack
        self._watchdog = watchdog
        self._logger = logging.getLogger(__name__)

    def handle_message(self, message: InboundMessage) -> None:
        self._watchdog.record_heartbeat("orchestrator")
        self._logger.info("handling message id=%s session=%s", message.message_id, message.session_key)
        self._set_slack_reaction(message, self.IN_PROGRESS_EMOJI)
        request = self._build_agent_request(message)
        try:
            result = self._agent.execute_session(request)
        except Exception as exc:  # pragma: no cover - defensive entry point
            self._logger.exception("runtime execution failed")
            self._session_store.record_failure(message, _render_session_for_archive(request), str(exc))
            self._replace_slack_reaction(message, remove_emoji=self.IN_PROGRESS_EMOJI, add_emoji=self.FAILURE_EMOJI)
            self._reply(message, f"CoderClaw failed to execute the request: {exc}")
            return

        self._session_store.record_success(message, _render_session_for_archive(request), result)
        self._replace_slack_reaction(message, remove_emoji=self.IN_PROGRESS_EMOJI, add_emoji=self.SUCCESS_EMOJI)
        self._reply(message, result.output_text)

    def _build_agent_request(self, message: InboundMessage) -> AgentSessionRequest:
        context_messages = message.context_messages or (
            AgentSessionMessage(
                channel=message.channel,
                message_ts=message.reply_target.message_ts,
                thread_ts=message.reply_target.thread_ts,
                user_id=message.user_id,
                text=message.text,
            ),
        )
        session_messages = tuple(
            item
            if isinstance(item, AgentSessionMessage)
            else AgentSessionMessage(
                channel=item.channel,
                message_ts=item.message_ts,
                thread_ts=item.thread_ts,
                user_id=item.user_id,
                text=item.text,
            )
            for item in context_messages
        )
        return AgentSessionRequest(
            session_key=message.session_key,
            channel=message.channel,
            messages=session_messages,
            latest_user_text=message.text,
        )

    def _reply(self, message: InboundMessage, text: str) -> None:
        if message.reply_target.channel is ChannelName.SLACK:
            self._slack.post_message(
                channel_id=message.reply_target.channel_id,
                thread_ts=message.reply_target.thread_ts,
                text=text,
            )

    def _set_slack_reaction(self, message: InboundMessage, emoji_name: str) -> None:
        if message.reply_target.channel is not ChannelName.SLACK:
            return
        try:
            self._slack.add_reaction(
                channel_id=message.reply_target.channel_id,
                timestamp=message.reply_target.message_ts,
                emoji_name=emoji_name,
            )
        except Exception:
            self._logger.exception("failed to add Slack reaction emoji=%s", emoji_name)

    def _replace_slack_reaction(self, message: InboundMessage, remove_emoji: str, add_emoji: str) -> None:
        if message.reply_target.channel is not ChannelName.SLACK:
            return
        try:
            self._slack.remove_reaction(
                channel_id=message.reply_target.channel_id,
                timestamp=message.reply_target.message_ts,
                emoji_name=remove_emoji,
            )
        except Exception:
            self._logger.exception("failed to remove Slack reaction emoji=%s", remove_emoji)

        try:
            self._slack.add_reaction(
                channel_id=message.reply_target.channel_id,
                timestamp=message.reply_target.message_ts,
                emoji_name=add_emoji,
            )
        except Exception:
            self._logger.exception("failed to add Slack reaction emoji=%s", add_emoji)


def _render_session_for_archive(request: AgentSessionRequest) -> str:
    rendered_messages = "\n".join(
        f"- [{message.message_ts}] {message.user_id or 'unknown'}: {message.text}" for message in request.messages
    )
    return "\n\n".join(
        part
        for part in [
            f"Agent session: {request.session_key}",
            f"{request.channel.value} thread context:\n{rendered_messages}" if rendered_messages else "",
            f"Latest user request:\n{request.latest_user_text}",
        ]
        if part
    )
