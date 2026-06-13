from __future__ import annotations

import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from coderclaw.agent_home import ensure_agent_home_layout
from coderclaw.channels.slack import SlackAdapter
from coderclaw.config import AppConfig
from coderclaw.logging_utils import configure_logging
from coderclaw.orchestrator import SessionOrchestrator
from coderclaw.queue import DurableMessageQueue
from coderclaw.restart import RestartController
from coderclaw.runtimes.codex import CodexRuntime
from coderclaw.session_store import SessionStore
from coderclaw.watchdog import Watchdog


class CoderClawApp:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._slack = SlackAdapter(
            bot_token=config.slack_bot_token,
            app_token=config.slack_app_token,
        )
        self._restart = RestartController(config.restart_lock_file)
        self._drain_logged = False
        self._watchdog = Watchdog(
            watch_paths=[
                config.repo_root / "src",
                config.repo_root / "README.md",
                config.repo_root / "AGENTS.md",
                config.memory_file,
                config.daily_memory_dir,
                config.coder_home_root / "skills",
            ],
            interval_seconds=config.watchdog_interval_seconds,
            stale_seconds=config.watchdog_stale_seconds,
            on_change=self.request_restart,
        )
        self._orchestrator = SessionOrchestrator(
            agent=CodexRuntime(
                codex_bin=config.codex_bin,
                repo_root=config.repo_root,
                timeout_seconds=config.codex_timeout_seconds,
            ),
            session_store=SessionStore(config.session_archive_dir),
            slack=self._slack,
            watchdog=self._watchdog,
        )
        self._queue = DurableMessageQueue(config.queue_state_file)

    def start(self) -> None:
        ensure_agent_home_layout(coder_home_root=self._config.coder_home_root)
        self._queue.start(self._orchestrator.handle_message)
        self._slack.start_socket_mode(self._queue.put)
        self._watchdog.record_heartbeat("server")
        self._watchdog.start()
        if not self._config.slack_bot_token:
            self._logger.warning("SLACK_BOT_TOKEN is not configured; Slack replies will fail")
        if not self._config.slack_app_token:
            self._logger.warning("SLACK_APP_TOKEN is not configured; Slack Socket Mode will not connect")

    def stop(self) -> None:
        self._slack.stop_socket_mode()
        self._queue.stop()
        self._watchdog.stop()

    def request_restart(self) -> None:
        if self._restart.is_requested():
            return
        self._logger.info("restart requested after source or doc change")
        self._restart.request_restart()

    def maybe_restart(self, server: ThreadingHTTPServer) -> bool:
        if not self._restart.is_requested():
            return False

        self._restart.prepare_for_restart(self._slack.stop_socket_mode)
        pending = self._queue.pending_count()
        active = self._queue.active_count()
        if pending or active:
            if not self._drain_logged:
                self._logger.info(
                    "restart requested; waiting for sessions to complete pending=%s active=%s",
                    pending,
                    active,
                )
                self._drain_logged = True
            return False

        self._logger.info("restart requested; all sessions completed, restarting process")
        self._restart.perform_restart(
            stop_runtime=lambda: self._stop_for_restart(server),
            reexec=_reexec_current_process,
        )
        return True

    def _stop_for_restart(self, server: ThreadingHTTPServer) -> None:
        server.server_close()
        self._slack.stop_socket_mode()
        self._queue.stop()
        self._watchdog.stop()

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "channel": "slack",
            "slack_transport": "socket_mode",
            "slack_connected": self._slack.is_socket_mode_connected(),
            "agent_boundary": "acp",
            "agent_adapter": "legacy-codex-cli",
            "coder_home_root": str(self._config.coder_home_root),
            "memory_file": str(self._config.memory_file),
            "daily_memory_dir": str(self._config.daily_memory_dir),
            "queue_state_file": str(self._config.queue_state_file),
            "session_archive_dir": str(self._config.session_archive_dir),
            "restart_requested": self._restart.is_requested(),
        }


def build_handler(app: CoderClawApp) -> type[BaseHTTPRequestHandler]:
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            app._watchdog.record_heartbeat("server")
            self._send_json(HTTPStatus.OK, app.health())

        def do_POST(self) -> None:  # noqa: N802
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            logging.getLogger("http").info("%s - %s", self.address_string(), format % args)

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return RequestHandler


def main() -> None:
    configure_logging()
    config = AppConfig.from_env()
    app = CoderClawApp(config)
    app.start()

    server = ThreadingHTTPServer((config.host, config.port), build_handler(app))
    server.timeout = 1
    logging.getLogger(__name__).info(
        "CoderClaw listening on http://%s:%s with Slack Socket Mode",
        config.host,
        config.port,
    )
    try:
        while True:
            server.handle_request()
            if app.maybe_restart(server):
                return
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("shutting down")
    finally:
        server.server_close()
        app.stop()


def _reexec_current_process() -> None:
    os.execv(sys.executable, [sys.executable, "-m", "coderclaw"])
