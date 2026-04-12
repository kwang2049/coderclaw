from __future__ import annotations

import logging
import os
from pathlib import Path


def ensure_agent_home_layout(repo_root: Path, coder_home_root: Path, codex_home: Path) -> None:
    logger = logging.getLogger(__name__)
    coder_home_root.mkdir(parents=True, exist_ok=True)
    codex_home.mkdir(parents=True, exist_ok=True)

    codex_symlink = repo_root / ".codex"
    try:
        if codex_symlink.exists() or codex_symlink.is_symlink():
            if codex_symlink.is_symlink() and codex_symlink.resolve() == codex_home.resolve():
                return
            logger.warning("existing .codex path does not match the configured project Codex home")
            return

        target = os.path.relpath(codex_home, start=repo_root)
        codex_symlink.symlink_to(target, target_is_directory=True)
        logger.info("created .codex symlink -> %s", target)
    except OSError as exc:
        logger.warning("failed to create .codex symlink: %s", exc)
