# .coder_home

This directory is the shared project-local home for coding agent CLIs used by CoderClaw.

Goals:

- keep agent steering and reusable local state under one root
- support multiple agent products behind a consistent layout
- allow agent-specific conventional folder names to exist as symlinks when needed

Current layout:

- `shared/`: shared project-local notes or future cross-agent state
- `codex/`: Codex-specific home used as `CODEX_HOME`

The runtime may create convenience symlinks such as:

- `.codex -> .coder_home/codex`

Mutable runtime artifacts such as auth tokens, caches, logs, and local config should remain untracked.

