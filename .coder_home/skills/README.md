# Skills

This directory is the portable skills registry for CoderClaw.

Goal:

- keep skills Markdown-first
- make them easy to adapt across multiple coding agent products
- avoid locking the repository to a single agent vendor's folder convention

Recommended layout:

```text
skills/<skill>/
  SKILL.md
  assets/...
  prompts/...
```

Compatibility guidance:

- `SKILL.md` is the canonical skill description in this repository.
- Agent-specific wrappers or mirrors may be added later if a runtime expects a different convention.
- Keep the core skill content portable so the same skill can be consumed by Codex, Claude Code, Gemini CLI, Kiro CLI, or future adapters.

