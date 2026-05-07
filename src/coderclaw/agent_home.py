from __future__ import annotations

import logging
from pathlib import Path


def ensure_agent_home_layout(coder_home_root: Path) -> None:
    logger = logging.getLogger(__name__)
    coder_home_root.mkdir(parents=True, exist_ok=True)
    (coder_home_root / "skills").mkdir(parents=True, exist_ok=True)
    logger.debug("ensured coder home skills layout at %s", coder_home_root)
