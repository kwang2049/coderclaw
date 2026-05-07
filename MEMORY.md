# MEMORY.md

Curated long-term memory for CoderClaw.

Use this file for durable facts, design decisions, stable preferences, and operating rules that should persist across sessions.

Current durable memory:

- Slack is the first communication channel.
- Codex is the first integrated coding runtime.
- Repo-root `AGENTS.md` is the static prompt entrypoint and source of truth for static prompt guidance.
- Repo-root `MEMORY.md` is the canonical long-term memory file.
- Daily working memory lives under `memory/daily/`.
- Skills live under `.coder_home/skills/` in a Markdown-first layout intended to remain portable across multiple coding agent products.
- `.agents/skills` is the Codex-compatible repo-level skills path and symlinks to `.coder_home/skills`.
- `.coder_home/` is reserved for skills rather than canonical prompt, memory, or runtime-state files.
- Static prompt assembly was removed; static prompt guidance now lives directly in repo-root `AGENTS.md`.
- Slack queue and active session persistence is local-first runtime state stored by default at `.coderclaw/state/queue.json`.
- Local bootstrap uses `scripts/install.sh`, requiring `python >= 3.11`.
- Local startup uses `scripts/start.sh`, which can restart an existing listener and writes timestamped logs under `.coderclaw/logs/`.
- Handled session exchanges are archived under `.coderclaw/sessions/` as JSONL files keyed by session.
- Automatic restart on watched file changes drains active/queued sessions before re-exec and uses `.coderclaw/state/restart.lock`.
- Runtime adapters should return structured execution metadata through `AgentResult.metadata` for cross-runtime observability.
