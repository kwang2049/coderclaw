# AGENTS.md

Canonical steering for coding agent products used with CoderClaw lives here.

This file merges the roles that might otherwise be split across separate files such as `SOUL.md` and `TOOLS.md`.

## Project Intent

CoderClaw is a local-first agentic system that wraps an existing coding agent CLI as the execution core while exposing the user experience through external communication channels such as Slack, Discord, and email.

The initial target agent is Codex, invoked through a command such as:

```bash
codex exec --skip-git-repo-check "$PROMPT"
```

The architecture must stay extensible so other agent runtimes can be added later, including Claude Code, Gemini CLI, and Kiro CLI.

The first communication channel for implementation is Slack.

## Markdown Conventions

- `AGENTS.md` is the merged steering file.
- `MEMORY.md` stores curated long-term memory.
- `memory/daily/YYYY-MM-DD.md` stores daily append-oriented working memory outside `.coder_home`.
- `skills/<skill>/SKILL.md` is the canonical portable skill format.

Memory maintenance rules:

- durable facts, stable preferences, and lasting design decisions belong in `MEMORY.md`
- short-horizon notes and daily context belong in `../memory/daily/YYYY-MM-DD.md`
- if the user says `remember this`, update the appropriate Markdown memory file as part of the task
- do not rely on hidden memory as the source of truth
- do not implement programmatic memory flushing unless explicitly requested

## Engineering Rules

- keep the system local-first
- preserve runtime-agnostic boundaries between agent adapters and orchestration
- prefer updating steering and memory before broader code mutation
- keep changes auditable and reversible where practical
- use Python 3.11 with a local `.venv` workflow unless the user explicitly directs otherwise
- treat `.coder_home` as the shared agent-home root; product-specific conventional homes may symlink here

