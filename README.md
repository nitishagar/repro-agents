# repro-agents

> **Agents that rerun your science and show their receipts.**

[![CI](https://github.com/nitishagar/repro-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/nitishagar/repro-agents/actions/workflows/ci.yml)
[![Docs](https://github.com/nitishagar/repro-agents/actions/workflows/docs.yml/badge.svg)](https://nitishagar.github.io/repro-agents/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A reference implementation of three agent patterns that act as **reproducibility
auditors** for scientific Python projects: environment forensics, notebook
linting, and result verification. **Auditors, not authors** — the toolkit runs
locally or in CI on *your own* project, and every output is a machine-checkable
**evidence bundle**, never a bare verdict.

> Companion repository to the article *"Reproducibility Is a Labor Problem.
> Agents Are Labor."* and the talk *"From Industry AI Agents to Open Science."*

## The Oracle Principle

The agent never asserts success. **Deterministic code grades every claim.** In
Pattern A, the grader is a clean-environment dependency solve plus a smoke-run
inside a rootless Docker sandbox — the LLM only *proposes* and *narrates*. Verdict
strings in every bundle are derived from oracle exit codes; LLM text is confined
to a clearly labelled `narrative` section. A self-check (`make security`) fails the
build if that line is ever crossed.

The core runs with **no LLM at all** (`--no-llm`) — both a safety story and an
adoption wedge.

## What repro-agents does today (Pattern A — environment forensics)

```bash
repro-agents audit path/to/project --no-llm
```

1. Walks every import in the project (AST).
2. Diffs imports against declared dependencies (`pyproject.toml` /
   `requirements.txt` / `environment.yml`), cross-checked with `deptry`.
3. Verifies every package name actually exists on PyPI (anti-slopsquat) — refuses
   to write a spec containing an unverified name.
4. Synthesizes a **minimal dependency spec** and **proves** it solves and
   smoke-runs in a rootless Docker sandbox (network off during execution).
5. Emits a diffable **evidence bundle**: `report.json` (schema-versioned) +
   `report.md` (human render) with findings, hashes, env fingerprint, tool
   versions, and a cost line.

## How this differs from `deptry` / `fawltydeps`

They **detect**. repro-agents detects → **repairs** (synthesizes a minimal spec)
→ **proves** (solves + smoke-runs in a sandbox) → **reports** (a diffable evidence
bundle). Detection is delegated to those tools (`--no-llm` mode literally *is*
deptry-and-friends); the value the loop adds is closing the loop and proving the fix.

## Install

```bash
uv tool install repro-agents          # once published
# or, from source:
git clone https://github.com/nitishagar/repro-agents && cd repro-agents
uv sync --extra dev --extra llm
```

Requires Python ≥ 3.10. Docker is required for the sandboxed solve/smoke-run.

## Development

This repo dogfoots its own backpressure philosophy. After every change:

```bash
make all                # ruff + mypy + unit tests + anti-theater self-check
make test-integration   # Docker-backed oracle + network tests
```

See [`AGENTS.md`](AGENTS.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), and the
[implementation plan](docs/plans/2026-06-11-repro-agents-v0.1-pattern-a.md).

## Status & roadmap

- **v0.1** — Pattern A (environment forensics), `--no-llm` + scaffolded agent loop. ← *here*
- **v0.2** — Pattern B (notebook cell-graph, disorder report, clean-kernel re-exec diff).
- **v0.3** — Pattern C (output tolerance compare, seed audit, figure hashing).
- **v0.4** — `repro-agents-action` (audit on PR, budget-capped).

## License

[Apache-2.0](LICENSE).
