# AGENTS.md

This file defines the root-level operating instructions for agents working in this repository. Its scope is the entire repository unless a deeper `AGENTS.md` overrides part of it.

## Project Intent

CoderClaw is a local-first agentic system that wraps an existing coding agent CLI as the execution core while exposing the user experience through external communication channels such as Slack, Discord, and email.

The initial target agent is Codex, invoked through a command such as:

```bash
codex exec --skip-git-repo-check "$PROMPT"
```

The architecture must stay extensible so other agent runtimes can be added later, including Claude Code, Gemini CLI, and Kiro CLI.

The first communication channel for implementation is Slack.

## Product Constraints

- The agent runtime and server program run on the user's own laptop or desktop.
- User requests arrive from external communication apps rather than a local terminal UI.
- The system must be resilient during long-running tasks.
- The system must support controlled self-improvement.
- The system must not assume cloud-only infrastructure for the core execution loop.

## Core System Responsibilities

The repository should evolve around these subsystems:

1. Channel adapters
2. Message queue and routing
3. Agent runtime adapters
4. Session orchestration
5. Watchdog and recovery
6. Memory and self-improvement pipeline
7. Policy, audit, and safety controls

## Architecture Guidance

### 1. Local-first runtime

- Prefer designs that run fully on a personal machine.
- Treat external services as optional integrations, not hard dependencies for core task execution.
- Keep setup simple enough for a single user to run locally.

### 2. Agent abstraction

- Do not couple orchestration code directly to Codex-specific behavior beyond the first integration layer.
- Introduce a clear runtime interface so each coding agent can be swapped behind a common contract.
- Keep prompt construction, process spawning, output parsing, and lifecycle management inside the runtime adapter layer.

### 3. Centralized messaging

- Communication apps should feed a unified internal message queue.
- Queue semantics should make retries, deduplication, ordering, and auditability explicit.
- Business logic should consume normalized messages rather than app-specific payloads.

### 4. Watchdog-first reliability

- Long-running agent work must be supervised.
- Design for process restart, stalled-session detection, and state recovery.
- Source-change monitoring should support safe reload or restart workflows for the local server.

### 5. Controlled self-improvement

Self-improvement is a first-class feature, but it must stay bounded.

- Prefer improving operational memory and `AGENTS.md` before broader code mutation.
- Any code-modifying self-improvement path must be explicit, reviewable, and auditable.
- Preserve a clear distinction between:
  - short-term task context
  - persistent memory
  - executable code
  - policy and guardrail documents

### 6. Safety and traceability

- Record why the system changed itself, not just what changed.
- Keep an audit trail for prompts, actions, edits, and approvals when feasible.
- Favor reversible operations and explicit checkpoints.

## Documentation Rules

- Keep `README.md` aligned with the actual architecture and operator workflow.
- When architecture, runtime flow, or operating assumptions change, update `README.md` and this file in the same work session.
- Prefer concise, operational documentation over aspirational prose.

## Engineering Conventions

- Build small, replaceable modules.
- Prefer typed interfaces and explicit boundaries between adapters, orchestration, and policy.
- Avoid premature framework complexity before the first end-to-end loop works locally.
- Default to portable tooling and straightforward local development commands.
- Add dependencies only when they clearly reduce complexity or operational risk.
- Use Python 3.11 with a local `.venv` workflow for this repository unless the user explicitly directs a change.
- Prefer Python standard library primitives for the bootstrap stage when they keep the system simple.
- Use a shared project-local `.coder_home` directory for agent-home state, with agent-specific subdirectories such as `.coder_home/codex`.
- When an agent CLI expects a conventional home folder name, prefer a symlink from that conventional name to the corresponding `.coder_home/<agent>` directory.

## Expected Initial Layout

As the project grows, favor a structure close to:

```text
.coder_home/
memory/
src/
  coderclaw/
    channels/
    runtimes/
    config.py
    memory.py
    orchestrator.py
    policy.py
    queue.py
    server.py
    watchdog.py
```

The exact layout may change, but keep the subsystem boundaries recognizable.

## Near-Term Priorities

1. Define the end-to-end local architecture.
2. Implement a Codex runtime adapter.
3. Add Slack as the first communication channel adapter.
4. Introduce a centralized message queue.
5. Add watchdog supervision and restart behavior.
6. Define memory files and self-improvement rules.

## Guardrails For Future Agents

- Do not hardcode secrets or machine-specific credentials into the repository.
- Do not implement unrestricted self-modification loops.
- Do not bypass queueing and supervision with direct channel-to-agent shortcuts unless there is a strong documented reason.
- Do not add provider-specific assumptions that would block multi-agent runtime support later.
- If implementation choices conflict with the local-first requirement, prefer the local-first design unless explicitly directed otherwise.

## Definition Of Done For Documentation Work

A documentation task is complete only when:

- the described architecture is internally consistent
- the operator workflow is clear
- the runtime boundaries are explicit
- the self-improvement constraints are documented
- `README.md` and `AGENTS.md` agree on the core system model
