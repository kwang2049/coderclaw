from __future__ import annotations

import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from coderclaw.agent_home import ensure_agent_home_layout
from coderclaw.channels.slack import SlackAdapter
from coderclaw.config import AppConfig
from coderclaw.logging_utils import configure_logging
from coderclaw.memory import MemoryStore
from coderclaw.orchestrator import SessionOrchestrator
from coderclaw.policy import SelfImprovementPolicy
from coderclaw.queue import InMemoryMessageQueue
from coderclaw.runtimes.codex import CodexRuntime
from coderclaw.watchdog import Watchdog


class CoderClawApp:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._slack = SlackAdapter(
            bot_token=config.slack_bot_token,
            signing_secret=config.slack_signing_secret,
        )
        self._watchdog = Watchdog(
            watch_paths=[
                config.repo_root / "src",
                config.repo_root / "README.md",
                config.repo_root / "AGENTS.md",
            ],
            interval_seconds=config.watchdog_interval_seconds,
            stale_seconds=config.watchdog_stale_seconds,
        )
        self._orchestrator = SessionOrchestrator(
            runtime=CodexRuntime(
                codex_bin=config.codex_bin,
                repo_root=config.repo_root,
                codex_home=config.codex_home,
                timeout_seconds=config.codex_timeout_seconds,
            ),
            memory_store=MemoryStore(config.memory_file),
            policy=SelfImprovementPolicy(),
            slack=self._slack,
            watchdog=self._watchdog,
        )
        self._queue = InMemoryMessageQueue()

    def start(self) -> None:
        ensure_agent_home_layout(
            repo_root=self._config.repo_root,
            coder_home_root=self._config.coder_home_root,
            codex_home=self._config.codex_home,
        )
        self._queue.start(self._orchestrator.handle_message)
        self._watchdog.record_heartbeat("server")
        self._watchdog.start()
        if not self._config.slack_bot_token:
            self._logger.warning("SLACK_BOT_TOKEN is not configured; Slack replies will fail")
        if not self._config.slack_signing_secret:
            self._logger.warning("SLACK_SIGNING_SECRET is not configured; non-verification events are insecure")

    def stop(self) -> None:
        self._queue.stop()
        self._watchdog.stop()

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "channel": "slack",
            "runtime": "codex",
            "coder_home_root": str(self._config.coder_home_root),
            "codex_home": str(self._config.codex_home),
            "memory_file": str(self._config.memory_file),
        }

    def handle_slack_event(self, raw_body: bytes, headers: dict[str, str]) -> tuple[int, dict[str, object]]:
        self._watchdog.record_heartbeat("server")
        payload = self._slack.decode(raw_body)
        if payload.get("type") == "url_verification":
            return HTTPStatus.OK, {"challenge": payload.get("challenge", "")}
        if not self._slack.verify_signature(raw_body, headers):
            return HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "invalid_slack_signature"}

        message = self._slack.extract_message(payload)
        if not message:
            self._logger.info("ignored Slack payload type=%s", payload.get("type"))
            return HTTPStatus.OK, {"ok": True, "ignored": True}

        self._queue.put(message)
        self._logger.info("queued Slack message id=%s", message.message_id)
        return HTTPStatus.ACCEPTED, {"ok": True, "queued": True, "message_id": message.message_id}


def build_handler(app: CoderClawApp) -> type[BaseHTTPRequestHandler]:
    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_json(HTTPStatus.OK, app.health())

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/slack/events":
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            headers = {key.lower(): value for key, value in self.headers.items()}
            status, payload = app.handle_slack_event(raw_body, headers)
            self._send_json(status, payload)

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
    logging.getLogger(__name__).info("CoderClaw listening on http://%s:%s", config.host, config.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("shutting down")
    finally:
        server.server_close()
        app.stop()
