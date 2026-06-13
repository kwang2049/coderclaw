from __future__ import annotations

import logging
import subprocess
import time
from datetime import UTC, datetime

from coderclaw.models import AgentResult, AgentSessionRequest, RuntimeExecutionMetadata


class CodexRuntime:
    def __init__(
        self,
        codex_bin: str,
        repo_root,
        timeout_seconds: int,
    ) -> None:
        self._codex_bin = codex_bin
        self._repo_root = repo_root
        self._timeout_seconds = timeout_seconds
        self._logger = logging.getLogger(__name__)

    def execute_session(self, request: AgentSessionRequest) -> AgentResult:
        return self.execute(_render_legacy_prompt(request))

    def execute(self, prompt: str) -> AgentResult:
        command = [
            self._codex_bin,
            "exec",
            "-s",
            "danger-full-access",
            "--skip-git-repo-check",
            prompt,
        ]
        self._logger.info("running Codex runtime command=%s", command[:5])
        started_at = datetime.now(UTC)
        start_time = time.monotonic()
        completed = subprocess.run(
            command,
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            check=False,
        )
        completed_at = datetime.now(UTC)
        metadata = RuntimeExecutionMetadata(
            runtime_name="codex",
            command=command,
            cwd=str(self._repo_root),
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_seconds=round(time.monotonic() - start_time, 6),
            exit_code=completed.returncode,
        )
        raw_output = (completed.stdout or "").strip()
        if completed.returncode != 0:
            error_output = (completed.stderr or "").strip()
            message = error_output or raw_output or "Codex exited without output."
            raise RuntimeError(f"Codex runtime failed: {message}")
        self._logger.info("Codex runtime completed successfully")
        return AgentResult(
            output_text=raw_output or "No response produced.",
            raw_output=raw_output,
            metadata=metadata,
        )


def _render_legacy_prompt(request: AgentSessionRequest) -> str:
    rendered_messages = "\n".join(
        f"- [{message.message_ts}] {message.user_id or 'unknown'}: {message.text}" for message in request.messages
    )
    return "\n\n".join(
        part
        for part in [
            "You are running inside CoderClaw through a communication-thread-driven local orchestration layer.",
            f"Agent session key: {request.session_key}",
            f"{request.channel.value} thread context:\n{rendered_messages}" if rendered_messages else "",
            f"Latest user request:\n{request.latest_user_text}",
        ]
        if part
    )
