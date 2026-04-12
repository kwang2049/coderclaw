# AGENTS.md

This root file is a repository compatibility layer.

Canonical steering for coding agent products lives in:

```text
.coder_home/AGENTS.md
```

Canonical long-term memory lives in:

```text
.coder_home/MEMORY.md
```

Canonical portable skills live in:

```text
.coder_home/skills/
```

Daily working memory remains outside the agent-home directory:

```text
memory/daily/YYYY-MM-DD.md
```

Repository rules:

- keep `README.md` aligned with `.coder_home/AGENTS.md`
- if you update Markdown steering or long-term memory conventions, update both this file and `.coder_home/AGENTS.md` in the same work session
- do not reintroduce separate `SOUL.md` or `TOOLS.md` files unless explicitly requested
- do not implement programmatic memory flushing unless explicitly requested
- treat `.coder_home` as the shared agent-home root for coding agent products
