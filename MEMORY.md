# MEMORY.md

Curated long-term memory for CoderClaw.

Use this file for durable facts, design decisions, stable preferences, and operating rules that should persist across sessions.

Current durable memory:

- Slack is the first communication channel.
- CoderClaw's project direction is to connect to coding agents through ACP (Agent Client Protocol).
- Each communication thread should map to a new coding-agent session.
- A thread's agent session context should be exactly the thread-visible context, plus the static project contract and any dynamic files the agent explicitly consults.
- Communication apps should primarily relay messages into and out of ACP-backed agent sessions rather than own hidden agent state.
- Codex CLI support exists as an earlier bootstrap path, but direct CLI wrapping is no longer the target architecture.
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
- Slack agent input should be built from the relevant Slack thread context, matching the thread-to-agent-session model.
- Slack app setup should be imported from repo-root `manifest.json`; current manifest enables Socket Mode and declares `app_mention` and `message.im` bot events plus `app_mentions:read`, `chat:write`, `reactions:write`, and `im:history` bot scopes.
- Slack direct messages require the App Home messages tab to remain enabled in `manifest.json`.
- Slack app manifest management is partially automated by `scripts/slack-app-validate.sh`, `scripts/slack-app-create.sh`, and `scripts/slack-app-update.sh`, using `SLACK_CONFIG_TOKEN`.
- Agent calls should return structured execution metadata through `AgentResult.metadata` or its ACP-era equivalent for cross-agent observability.
- The codebase now has an internal `coderclaw.acp.AgentClient` boundary with typed `AgentSessionRequest` / `AgentSessionMessage` models; the existing Codex CLI path is a legacy adapter behind that boundary.
- Slack context collection is thread-scoped: top-level messages use their own thread context rather than neighboring channel history.
