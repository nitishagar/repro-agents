# Architecture

## Principles

1. **Oracle Principle** — deterministic code grades every claim; the LLM only
   proposes and narrates.
2. **Wrap, don't reimplement** — detection delegates to `deptry`, `uv`, the
   stdlib `ast`, and (later) `nbformat`/`nbclient`/`nbdime`.
3. **Local-first / auditor posture** — no auto-PRs, ever.
4. **Budgets everywhere** — token / wall-clock / attempt caps; a cost line in
   every bundle.
5. **`--no-llm` always works.**

## The Pattern A pipeline

```
collect imports (ast)
  → diff vs declared deps (+ deptry cross-check)
  → verify undeclared names on PyPI (anti-slopsquat, fail-closed)
  → synthesize a minimal spec
  → PROVE: solve + smoke-run in the sandbox oracle (network off on execute)
  → assemble evidence bundle (report.json + report.md)
```

## Module map (`src/repro_agents/`)

| Module | Role |
| --- | --- |
| `tools/imports.py` | AST import inventory. |
| `tools/registry.py` | import→distribution map + PyPI existence + allowlist. |
| `tools/deps.py` | parse declared deps; diff; `deptry` cross-check. |
| `tools/sandbox.py` | `DockerSandbox` (secure oracle) and `LocalSandbox`. |
| `tools/solver.py` | spec synthesis + `prove()` (exit-code verdict). |
| `report/` | schema-versioned bundle + markdown render. |
| `budget.py` | token / wall-clock / attempt caps. |
| `agents/loop.py` | propose → verify → oracle → repeat state machine. |
| `agents/models.py` | `Model` protocol + `FakeModel`. |
| `agents/adapters/` | thin framework adapters (smolagents). |
| `cli.py` | `repro-agents audit \| version`. |

## The agent loop

The loop lives in the core so adapters stay thin (<100 lines). It proposes a spec,
runs every proposed name through the same anti-slopsquat check, asks the oracle to
prove it, reads the failure, and tries again — all bounded by a `Budget`. The
verdict is always the oracle's `Proof`, never the model's words.
