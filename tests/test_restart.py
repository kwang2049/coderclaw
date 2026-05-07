from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coderclaw.restart import RestartController


class RestartControllerTests(unittest.TestCase):
    def test_prepare_for_restart_stops_intake_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = RestartController(Path(tmpdir) / "restart.lock")
            calls: list[str] = []

            controller.request_restart()
            controller.prepare_for_restart(lambda: calls.append("stop"))
            controller.prepare_for_restart(lambda: calls.append("stop"))

            self.assertEqual(calls, ["stop"])

    def test_perform_restart_calls_stop_and_reexec(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            controller = RestartController(Path(tmpdir) / "restart.lock")
            calls: list[str] = []

            controller.perform_restart(
                stop_runtime=lambda: calls.append("stop"),
                reexec=lambda: calls.append("reexec"),
            )

            self.assertEqual(calls, ["stop", "reexec"])


if __name__ == "__main__":
    unittest.main()
