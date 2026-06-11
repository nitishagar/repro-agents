# Contributing to repro-agents

Thanks for helping make science reproducible! This project values **deterministic
backpressure**: contributions are gated by a build target, not by vibes.

## Getting started

```bash
git clone https://github.com/nitishagar/repro-agents && cd repro-agents
uv sync --extra dev --extra llm
uv run pre-commit install
make all          # must be green before you start
```

Requires Python ≥ 3.10 (managed by `uv`) and Docker (for the sandbox tests).

## The development loop

1. Write the test first (TDD). Unit tests go in `tests/unit/` and must not require
   Docker or the network. Tests that do go in `tests/integration/` and are marked
   `@pytest.mark.integration`.
2. Implement until `make all` is green.
3. For sandbox/oracle changes, also run `make test-integration`.
4. Open a PR. CI runs `make all` on Python 3.10–3.12 plus the Docker integration job.

## Good first issues

- **New fault types for `repro-gym`** (`benchmarks/repro-gym/`): a programmatic
  injection (e.g. unpin a version with a known API break, shuffle notebook cells).
- **New framework adapters** (`src/repro_agents/agents/adapters/`): keep adapters
  under ~100 lines — the loop state machine lives in the core.
- **New comparison strategies** (Pattern C): array tolerance, table compare, figure
  perceptual hash.
- **Curated `import → distribution` mappings** in `tools/registry.py`.

## Ground rules

- Respect the [design principles](AGENTS.md): Oracle Principle, wrap-don't-reimplement,
  local-first (no auto-PRs to other repos), budgets, `--no-llm` always works.
- New verdicts must come from oracle exit codes. The `make security` self-check
  will reject LLM-authored verdicts.

By contributing you agree your work is licensed under [Apache-2.0](LICENSE).
