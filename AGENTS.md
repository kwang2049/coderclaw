# AGENTS.md

This file is the static prompt entrypoint for CoderClaw.

Record static prompt guidance directly in this file, organized by section.

Repository rules:

- keep `README.md` aligned with this `AGENTS.md` contract
- do not reintroduce separate `SOUL.md` or `TOOLS.md` files unless explicitly requested
- do not implement programmatic memory flushing unless explicitly requested
- keep `.coder_home/` limited to coding-agent skills

## Project Intent

CoderClaw is a local-first agentic system that connects external communication channels such as Slack, Discord, and email to coding agents through ACP (Agent Client Protocol).

ACP is the primary boundary between CoderClaw and coding agents. CoderClaw should behave as an ACP client that starts or connects to an agent session, sends user-visible thread context as messages, receives agent output, and relays that output back to the communication app.

Each communication thread maps to a new coding-agent session. The agent's context for that session must be exactly the context visible in the communication thread, plus the static project contract and any dynamic files the agent elects to consult. Do not preserve hidden cross-thread agent context as an implicit input.

Communication apps should primarily behave as message relays. They collect inbound messages, construct the thread-scoped context, send it to the ACP-backed agent session, and post agent responses back into the same thread. Channel-specific behavior should stay thin and should not become the source of agent state.

The architecture must stay extensible so any coding agent with an ACP-compatible interface can be added without changing the communication-channel model.

The first communication channel for implementation is Slack.
Slack should connect through Socket Mode so the local-first deployment does not depend on a public webhook tunnel for normal Slack operation.

## Context Model

Use `AGENTS.md` as the static prompt contract.

Dynamic context is referenced from here and should be consulted only when useful for the task:

- `MEMORY.md` stores curated long-term memory and durable project conventions.
- `memory/daily/YYYY-MM-DD.md` stores daily working context and short-horizon notes.
- `.coder_home/skills/<skill>/SKILL.md` stores portable coding-agent skills following the chosen agent's official skill/home convention.
- `.agents/skills` may be used as a compatibility path for agent-specific repo conventions, backed by the shared `.coder_home/skills/` store.

For any new coding agent choice, first refer to that agent's official guide for setting up project- or workspace-level skills before deciding the local `.coder_home/skills/` layout.

Example:

- Codex skills guide: `https://developers.openai.com/codex/skills`

Memory maintenance rules:

- durable facts, stable preferences, and lasting design decisions belong in `MEMORY.md`
- short-horizon notes and daily context belong in `memory/daily/YYYY-MM-DD.md`
- if the user says `remember this`, update the appropriate Markdown memory file as part of the task
- do not rely on hidden memory as the source of truth

## Engineering Rules

- keep the system local-first
- preserve ACP-centered boundaries between communication channels, session orchestration, and coding agents
- treat communication threads as the authoritative unit of agent session context
- prefer updating `AGENTS.md` or Markdown memory before broader code mutation
- keep changes auditable and reversible where practical
- use Python 3.11 with a local `.venv` workflow unless the user explicitly directs otherwise
- keep `.coder_home/skills/` as the durable customization surface under `.coder_home`
- `conclude the session` means update the relevant Markdown files to reflect current project status, then create a git commit
