from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coderclaw.models import AgentSessionMessage, AgentSessionRequest, ChannelName
from coderclaw.runtimes.codex import CodexRuntime


class CodexRuntimeTests(unittest.TestCase):
    def test_returns_structured_execution_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fake_codex = root / "codex"
            fake_codex.write_text("#!/bin/sh\nprintf 'result from %s' \"$5\"\n", encoding="utf-8")
            fake_codex.chmod(0o755)
            runtime = CodexRuntime(
                codex_bin=str(fake_codex),
                repo_root=root,
                timeout_seconds=5,
            )

            result = runtime.execute("hello")

            self.assertEqual(result.output_text, "result from hello")
            self.assertIsNotNone(result.metadata)
            assert result.metadata is not None
            self.assertEqual(result.metadata.runtime_name, "codex")
            self.assertEqual(
                result.metadata.command[:5],
                [str(fake_codex), "exec", "-s", "danger-full-access", "--skip-git-repo-check"],
            )
            self.assertEqual(result.metadata.cwd, str(root))
            self.assertEqual(result.metadata.exit_code, 0)
            self.assertGreaterEqual(result.metadata.duration_seconds, 0)

    def test_execute_session_renders_thread_context_for_legacy_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            fake_codex = root / "codex"
            fake_codex.write_text("#!/bin/sh\nprintf '%s' \"$5\"\n", encoding="utf-8")
            fake_codex.chmod(0o755)
            runtime = CodexRuntime(
                codex_bin=str(fake_codex),
                repo_root=root,
                timeout_seconds=5,
            )

            result = runtime.execute_session(
                AgentSessionRequest(
                    session_key="slack:C123:1710000000.000000",
                    channel=ChannelName.SLACK,
                    latest_user_text="run tests",
                    messages=(
                        AgentSessionMessage(
                            channel=ChannelName.SLACK,
                            message_ts="1710000000.000000",
                            thread_ts="1710000000.000000",
                            user_id="U111",
                            text="root request",
                        ),
                        AgentSessionMessage(
                            channel=ChannelName.SLACK,
                            message_ts="1710000000.000100",
                            thread_ts="1710000000.000000",
                            user_id="U222",
                            text="run tests",
                        ),
                    ),
                )
            )

            self.assertIn("Agent session key: slack:C123:1710000000.000000", result.output_text)
            self.assertIn("[1710000000.000000] U111: root request", result.output_text)
            self.assertIn("Latest user request:\nrun tests", result.output_text)


if __name__ == "__main__":
    unittest.main()
