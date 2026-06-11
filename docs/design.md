# Design & plan

The full, backpressure-driven implementation plan (current state, phases, build
target, and what's explicitly out of scope) lives in the repository:

- [v0.1 Pattern A plan](plans/2026-06-11-repro-agents-v0.1-pattern-a.md)
- [Build state / handoff](plans/HANDOFF-2026-06-11.md)

## Roadmap

| Version | Scope |
| --- | --- |
| **v0.1** | Pattern A (environment forensics), `--no-llm` + scaffolded agent loop. ← *here* |
| v0.2 | Pattern B — notebook cell-graph, disorder report, clean-kernel re-exec diff. |
| v0.3 | Pattern C — output tolerance compare, seed audit, figure perceptual hashing. |
| v0.4 | `repro-agents-action` — audit on PR, budget-capped. |

## Positioning

`deptry`/`fawltydeps` **detect**. repro-agents detects → **repairs** (synthesizes a
minimal spec) → **proves** (solves + smoke-runs in a sandbox) → **reports** (a
diffable evidence bundle). Detection is delegated; the value the loop adds is
closing the loop and proving the fix.
