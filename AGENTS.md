# AGENTS.md

This file is the static prompt entrypoint for CoderClaw.

Record static prompt guidance directly in this file, organized by section.

Repository rules:

- keep `README.md` aligned with this `AGENTS.md` contract
- do not reintroduce separate `SOUL.md` or `TOOLS.md` files unless explicitly requested
- do not implement programmatic memory flushing unless explicitly requested
- keep `.coder_home/` limited to coding-agent skills

## Project Intent

CoderClaw is a local-first agentic system that wraps an existing coding agent CLI as the execution core while exposing the user experience through external communication channels such as Slack, Discord, and email.

The initial target agent is Codex, invoked through a command such as:

```bash
codex exec -s danger-full-access --skip-git-repo-check "$PROMPT"
```

The architecture must stay extensible so other agent runtimes can be added later, including Claude Code, Gemini CLI, and Kiro CLI.

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
- preserve runtime-agnostic boundaries between agent adapters and orchestration
- prefer updating `AGENTS.md` or Markdown memory before broader code mutation
- keep changes auditable and reversible where practical
- use Python 3.11 with a local `.venv` workflow unless the user explicitly directs otherwise
- keep `.coder_home/skills/` as the durable customization surface under `.coder_home`
- `conclude the session` means update the relevant Markdown files to reflect current project status, then create a git commit
