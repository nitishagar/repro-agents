# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository. This repo
dogfoods its own thesis: deterministic backpressure over non-deterministic suggestions.

## Code Quality (mandatory)

After **every** code change you MUST run:

```bash
make all
```

This runs `ruff` (lint + format check), `mypy` (types), the deterministic unit
tests, and the anti-theater self-check. **Resolve every failure before
proceeding.** When the build target exits non-zero, treat its output as the
authoritative instruction to fix.

For changes touching the sandbox/oracle, also run:

```bash
make test-integration   # requires Docker
```

## Non-negotiable design principles

1. **Oracle Principle.** The agent never asserts success. Deterministic code (the
   sandbox solve + smoke-run) grades every claim. A "verdict"/"status" field may
   only be derived from an oracle exit code — never from LLM text. LLM output lives
   in a clearly labelled `narrative` field. `make security` enforces this.
2. **Wrap, don't reimplement.** Delegate detection to existing tools (deptry,
   nbformat/AST, nbclient, uv, nbdime). The value here is loop-closing and proof.
3. **Local-first / auditor posture.** No auto-PRs, no upstream writes, **ever**.
   Optional local `.patch` output only.
4. **Budgets everywhere.** Hard caps on tokens, wall-clock, and solve attempts.
   Every bundle prints a cost line.
5. **`--no-llm` must always work.** The deterministic core never depends on an LLM.

## Disclosure policy (for this repository)

This project's own commit history and docs are partly authored with AI assistance.
That assistance is disclosed and every change is gated by the deterministic build
target above. We do not open automated PRs against other people's repositories.

## Repository map

See [`docs/plans/2026-06-11-repro-agents-v0.1-pattern-a.md`](docs/plans/2026-06-11-repro-agents-v0.1-pattern-a.md)
for the module map and phased plan.
