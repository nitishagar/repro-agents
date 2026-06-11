# repro-agents

> **Agents that rerun your science and show their receipts.**

`repro-agents` is a reference implementation of agent patterns that act as
**reproducibility auditors** for scientific Python projects. Auditors, not
authors — it runs locally or in CI on *your own* project, and every output is a
machine-checkable **evidence bundle**, never a bare verdict.

## The Oracle Principle

The agent never asserts success. **Deterministic code grades every claim.** In
Pattern A the grader is a clean-environment dependency solve plus a smoke-run
inside a rootless Docker sandbox; the LLM only *proposes* and *narrates*. Verdicts
in every bundle come from oracle exit codes, and a build-time self-check fails CI
if LLM text is ever used as a verdict.

The whole core runs with **no LLM at all** (`--no-llm`) — both a safety story and
an adoption wedge.

## What v0.1 does — Pattern A (environment forensics)

```bash
repro-agents audit path/to/project --no-llm
```

1. Walk every import (AST).
2. Diff imports against declared dependencies, cross-checked with `deptry`.
3. Verify every package name exists on PyPI (anti-slopsquat) — refuse to write a
   spec containing an unverified name.
4. Synthesize a minimal dependency spec and **prove** it solves + smoke-runs in a
   rootless Docker sandbox (network off during execution).
5. Emit a diffable evidence bundle (`report.json` + `report.md`).

## Next

- [Usage](usage.md) — install and run an audit.
- [Architecture](architecture.md) — how the pieces fit.
- [Security](security.md) — the threat model for executing untrusted code.
- [Design & plan](design.md) — the full implementation plan.
