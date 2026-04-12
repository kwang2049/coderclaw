from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from coderclaw.models import AgentResult


class CodexRuntime:
    def __init__(self, codex_bin: str, repo_root: Path, codex_home: Path, timeout_seconds: int) -> None:
        self._codex_bin = codex_bin
        self._repo_root = repo_root
        self._codex_home = codex_home
        self._timeout_seconds = timeout_seconds
        self._logger = logging.getLogger(__name__)

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
        completed = subprocess.run(
            command,
            cwd=self._repo_root,
            env={**os.environ, "CODEX_HOME": str(self._codex_home)},
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            check=False,
        )
        raw_output = (completed.stdout or "").strip()
        if completed.returncode != 0:
            error_output = (completed.stderr or "").strip()
            message = error_output or raw_output or "Codex exited without output."
            raise RuntimeError(f"Codex runtime failed: {message}")
        self._logger.info("Codex runtime completed successfully")
        return AgentResult(output_text=raw_output or "No response produced.", raw_output=raw_output)
