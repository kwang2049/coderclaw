from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
