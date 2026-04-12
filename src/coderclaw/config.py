from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    repo_root: Path
    coder_home_root: Path
    codex_home: Path
    memory_file: Path
    daily_memory_dir: Path
    codex_bin: str
    codex_timeout_seconds: int
    watchdog_interval_seconds: int
    watchdog_stale_seconds: int
    slack_bot_token: str | None
    slack_signing_secret: str | None

    @classmethod
    def from_env(cls) -> "AppConfig":
        repo_root = Path(os.getenv("CODERCLAW_REPO_ROOT", ".")).resolve()
        load_dotenv(repo_root / ".env")
        coder_home_root = Path(os.getenv("CODERCLAW_HOME_ROOT", ".coder_home"))
        codex_home = Path(os.getenv("CODERCLAW_CODEX_HOME", str(coder_home_root)))
        memory_file = Path(os.getenv("CODERCLAW_MEMORY_FILE", str(coder_home_root / "MEMORY.md")))
        daily_memory_dir = Path(os.getenv("CODERCLAW_DAILY_MEMORY_DIR", "memory/daily"))
        return cls(
            host=os.getenv("CODERCLAW_HOST", "127.0.0.1"),
            port=_env_int("CODERCLAW_PORT", 8787),
            repo_root=repo_root,
            coder_home_root=(repo_root / coder_home_root).resolve(),
            codex_home=(repo_root / codex_home).resolve(),
            memory_file=(repo_root / memory_file).resolve(),
            daily_memory_dir=(repo_root / daily_memory_dir).resolve(),
            codex_bin=os.getenv("CODERCLAW_CODEX_BIN", "codex"),
            codex_timeout_seconds=_env_int("CODERCLAW_CODEX_TIMEOUT_SECONDS", 1800),
            watchdog_interval_seconds=_env_int("CODERCLAW_WATCHDOG_INTERVAL_SECONDS", 5),
            watchdog_stale_seconds=_env_int("CODERCLAW_WATCHDOG_STALE_SECONDS", 60),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
        )
