# repro-agents v0.1 (Pattern A: Environment Forensics) — Implementation Plan

> Backpressure-driven, TDD plan. Companion repo to *"Reproducibility Is a Labor Problem. Agents Are Labor."*

## Overview

Build a **working, CI-green, public** first release of `repro-agents`: a reproducibility
**auditor** for scientific Python projects. v0.1 ships **Pattern A — environment
forensics** end-to-end:

```
repro-agents audit <path> --no-llm
```

walks imports, diffs them against declared dependencies, verifies every package name
actually exists on PyPI (anti-slopsquat), synthesizes a minimal dependency spec, and
**proves** that spec solves + smoke-runs **inside a rootless Docker sandbox** — then emits
a diffable **evidence bundle** (`report.json` + `report.md`). The LLM agent loop is built
as a framework-agnostic state machine, exercised against a **fake model** so the build
stays deterministic; wiring a live Claude model is a documented, non-blocking next step.

**Design north star (the Oracle Principle):** the agent never asserts success. Deterministic
code (the sandbox solve + smoke-run) grades every claim. LLM output is *narration and
proposal only*.

## Current State Analysis

Greenfield repo. No prior code.

### Test Baseline
- Test suite status: **none yet** (0 tests). Phase 0 establishes a green baseline.
- Build target status: **none yet**. Phase 0 defines `make all`.
- Coverage gaps: everything; built test-first per phase.

### Environment ground truth (verified 2026-06-11)
- `gh` active account is **`nagarwal-godaddy`**, NOT `nitishagar` (both are logged in).
  → Every `gh repo create` / `git push` MUST be preceded by `gh auth switch --user nitishagar`
  and a `gh auth status` assertion. Abort the push if active ≠ nitishagar.
- Git identity already `Nitish Agarwal <1592163+nitishagar@users.noreply.github.com>`
  (also pinned locally in the repo).
- Names free: PyPI `repro-agents` (404), GitHub `nitishagar/repro-agents` (absent).
- System Python is 3.9.6 (too old). `uv 0.9.26` provisions the project interpreter
  (target `>=3.10`, develop/CI on 3.12). Docker 29.5.2 available. `pixi` absent (uv-first).

## Desired End State

A public `github.com/nitishagar/repro-agents` repo where:
- `repro-agents audit examples/<demo> --no-llm` runs and writes a real evidence bundle.
- `make all` is green locally and in CI (lint + typecheck + unit tests + security scan).
- A Docker-backed integration suite proves the solve/smoke-run oracle actually works.
- A MkDocs Material docs site is live on **GitHub Pages**.
- History is a sequence of small, green, TDD milestone commits.

### Key Discoveries (verified library facts, June 2026)
- **smolagents 1.26.0** — Anthropic via `LiteLLMModel(model_id="anthropic/…")` + extra
  `smolagents[litellm]`; `@tool` decorator; `CodeAgent`/`ToolCallingAgent`; `max_steps` cap;
  `RunResult`/`TokenUsage` for budgets. Requires Python ≥3.10.
- **deptry 0.25.1** — no Python API; `deptry <path> --json-output f.json`; codes `DEP001`
  (imported-undeclared) / `DEP002` (declared-unused); exits **non-zero when it finds
  violations** (do NOT treat as a hard error). Repo moved to `osprey-oss/deptry`.
- **uv** — `uv pip compile` (solve) → `uv venv` + `uv pip sync`/`install` (clean env) →
  `<venv>/bin/python -c "import …"` (smoke-run). Two-step lets us keep **network on for
  solve, off for execute**.
- **`importlib.metadata.packages_distributions()`** maps import→distribution but only for
  *installed* packages → pair with a PyPI JSON existence check + a curated override table
  (`sklearn`→`scikit-learn`, `cv2`→`opencv-python`, `PIL`→`pillow`, `yaml`→`PyYAML`, …).
- **nbformat 5.10.4 / nbclient 0.11.0 / nbdime 4.0.4** — for Patterns B/C (later milestones).

### External Validation
- **Pimentel et al. (MSR 2019), CORE-Bench, PaperBench, REPRO-Bench**: full-paper
  reproduction is out of reach for agents → scope to **chore-sized, oracle-checkable** tasks.
  This plan does exactly that (dep forensics, not paper replication).
- **Governance climate (SciPy AGENTS.md proposal; matplotlib human-only PR policy)**: the
  **local-auditor, no-auto-PR** posture is the only one that earns trust now → enforced as a
  non-negotiable design principle (no upstream writes; optional local `.patch` only).

## What We're NOT Doing (v0.1)
- ❌ Pattern B (notebook cell-graph / disorder / re-exec) — v0.2.
- ❌ Pattern C (output tolerance compare / seed audit / figure hashing) — v0.3.
- ❌ GitHub Action `repro-agents-action` — v0.4.
- ❌ Full `repro-gym` benchmark harness — stub dir + README only; test fixtures are the seed.
- ❌ Auto-PRs / any upstream writes — **ever**. Optional local `--suggest-patch` only (later).
- ❌ Live LLM calls in the test suite / CI build target — scaffolded + fake-model tested only.
- ❌ R support, Quarto/myst audits, sigstore signing — schema reserves a `provenance` field.
- ❌ PyPI publish — name reserved conceptually; no release this milestone.

## Build Target Definition (MANDATORY — inner-loop backpressure)

**File:** `Makefile` (thin wrappers over `uv`-managed tools).

```makefile
.PHONY: install build lint format typecheck test test-integration security all docs clean

install:            ## create env + install dev/llm extras
	uv sync --extra dev --extra llm

build:
	uv build

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy src

test:               ## fast, deterministic, no Docker / no network
	uv run pytest -m "not integration" -q

test-integration:   ## Docker-backed oracle + network tests
	uv run pytest -m integration -q

security:           ## dependency CVEs + anti-theater grep (no LLM-authored verdicts)
	uv run pip-audit || true
	uv run python -m repro_agents._selfcheck

all: lint typecheck test security   ## <-- the inner loop. Run after EVERY change.

docs:
	uv run mkdocs build --strict
```

**AGENTS.md / CLAUDE.md instruction (added to the repo):**
> ## Code Quality
> After every code change you MUST run `make all`. Resolve every failure
> (lint, type, test, security) before proceeding. Docker-backed checks: `make test-integration`.

`repro_agents._selfcheck` is a deterministic guard implementing the doc's anti-theater rule:
it fails (exit 1) if any verdict/`status` string in the codebase or a rendered bundle is
produced from LLM text rather than an oracle exit code.

## Backpressure Strategy

Complexity = **High/Highest** (executes untrusted code in Docker; multi-component; public).

### Inner Loop (after every change)
- `make all` → `ruff` (lint+format) + `mypy` (types) + `pytest -m "not integration"` + `make security`.

### Outer Loop (phase completion / CI)
- `.pre-commit-config.yaml`: ruff, ruff-format, mypy, end-of-file/trailing-whitespace, `pip-audit`.
- `.github/workflows/ci.yml`: matrix Py 3.10/3.11/3.12 → `make all`; a Docker job → `make test-integration`.
- `.github/workflows/docs.yml`: `mkdocs build --strict` → deploy to Pages.

### Human Checkpoints
- **Outward-facing gate (Phase 0):** creating the **public** repo under `nitishagar`. Verify
  `gh` active user immediately before. (Pre-authorized by the user: public + Pages.)
- Report at each milestone; commits are individually reviewable in history.

## Implementation Approach

Framework-agnostic core; thin adapters. The Pattern-A loop state machine lives in
`agents/loop.py` (testable without any LLM); the smolagents adapter is <100 lines.

**TDD cycle per phase:** define test criteria → write failing tests → implement → `make all`
green → milestone commit → `gh auth switch --user nitishagar` (verify) → push.

### Module map (`src/repro_agents/`)
```
tools/imports.py    AST import walk → third-party top-level import names
tools/registry.py   import→distribution map + PyPI existence + allowlist (anti-slopsquat)
tools/deps.py       parse pyproject/requirements/environment.yml; diff; deptry cross-check
tools/sandbox.py    Sandbox protocol; DockerSandbox (rootless, net-off exec); LocalSandbox (tests)
tools/solver.py     synthesize minimal spec → solve → smoke-run → deterministic result
report/schema.py    schema-versioned dataclasses for report.json (+ provenance field)
report/bundle.py    assemble + write report.json
report/render.py    report.md human render
budget.py           token / wall-clock / attempt caps + cost line
agents/models.py    Model protocol + FakeModel (scripted, deterministic)
agents/loop.py      propose→execute oracle→read failure→tighten→emit bundle state machine
agents/envforensics.py  Pattern A wiring (tools + loop)
agents/adapters/smolagents_adapter.py  smolagents↔Model protocol
cli.py              typer: audit | lint-nb | verify  [--no-llm] [--budget]
_selfcheck.py       anti-theater deterministic guard
```

---

## Phase 0 — Repo bootstrap + build target + CI + public repo

### Test Criteria (FIRST)
- [ ] `uv run pytest -q` collects ≥1 test and passes (a `test_version` smoke test).
- [ ] `make all` exits 0 (lint+typecheck+test+security all green) on a clean checkout.
- [ ] `import repro_agents; repro_agents.__version__ == "0.1.0"`.

### Changes
- `pyproject.toml` (hatchling, src layout, `requires-python=">=3.10"`, Apache-2.0; deps:
  `typer`, `rich`, `deptry`, `packaging`, `tomli; python_version<'3.11'`; extras `llm`/`nb`/`dev`;
  script `repro-agents = "repro_agents.cli:main"`; ruff + mypy + pytest config).
- `src/repro_agents/__init__.py` (`__version__`), `_selfcheck.py` (initial no-op guard + 1 rule).
- `tests/unit/test_version.py`.
- `LICENSE` (Apache-2.0), `README.md`, `.gitignore`, `Makefile`, `.pre-commit-config.yaml`,
  `AGENTS.md`, `SECURITY.md`, `CONTRIBUTING.md`.
- `.github/workflows/ci.yml`.

### Success Criteria
**Inner loop:** `make all` passes.
**Outer loop:** push triggers CI; CI green on 3.10/3.11/3.12.
**Manual / outward-facing gate:** `gh auth switch --user nitishagar` → `gh auth status` shows
nitishagar active → `gh repo create nitishagar/repro-agents --public --source . --remote origin --push`.

---

## Phase 1 — `tools/imports.py` (AST import inventory)

### Test Criteria (FIRST)
- [ ] Returns third-party top-level names from `import a`, `import a.b`, `from a import b`.
- [ ] Excludes the stdlib (via `sys.stdlib_module_names`) and first-party/local modules.
- [ ] Skips relative imports; handles `try/except ImportError` and nested function imports.
- [ ] Syntax-error files are reported as warnings, not crashes.

### Changes
- `tools/imports.py`: `collect_imports(project_dir) -> ImportInventory` (names + per-name locations).
- `tests/unit/test_imports.py` + tiny fixture trees.

### Success Criteria
**Inner:** `make all`. **Outer:** CI green. **Manual:** spot-check on a real repo.

---

## Phase 2 — `tools/registry.py` (import→dist map + PyPI existence + allowlist)

### Test Criteria (FIRST)
- [ ] `import_to_distribution("sklearn") == "scikit-learn"` (override table + packages_distributions).
- [ ] PyPI existence check behind an **injectable** fetcher: `exists("requests")→True`,
      `exists("totally-not-real-xyz")→False` (mocked in unit).
- [ ] `verify_names(...)` refuses (raises/flags) any name failing existence → anti-slopsquat.
- [ ] Allowlist short-circuits existence checks for vetted names.
- [ ] One `@pytest.mark.integration` test hits real PyPI for a known package.

### Changes
- `tools/registry.py`: override table, `import_to_distribution`, `PyPIClient` (injectable),
  `verify_names`, allowlist.
- `tests/unit/test_registry.py`, `tests/integration/test_registry_pypi.py`.

---

## Phase 3 — `tools/deps.py` (declared-dep parsing + diff + deptry cross-check)

### Test Criteria (FIRST)
- [ ] Parse declared distributions from `pyproject.toml` (`[project].dependencies` + optional),
      `requirements.txt`, `environment.yml` → normalized distribution names.
- [ ] `diff(imports, declared) -> {undeclared, unused}` using registry mapping + normalization.
- [ ] deptry wrapper parses `DEP001`/`DEP002` from `--json-output`; subprocess **mocked** in unit;
      tolerates deptry's non-zero exit; absence of deptry degrades gracefully.
- [ ] One `@pytest.mark.integration` test runs real deptry on a fixture.

### Changes
- `tools/deps.py`: `parse_declared(...)`, `diff(...)`, `run_deptry(...)`.
- `tests/unit/test_deps.py`, `tests/integration/test_deptry.py`, fixtures.

---

## Phase 4 — `tools/sandbox.py` + `tools/solver.py` (the Oracle)

### Test Criteria (FIRST)
- [ ] `Sandbox` protocol: `solve(spec)`, `smoke_run(spec, imports)` → `(ok: bool, log, artifacts)`.
- [ ] `LocalSandbox` (subprocess+uv) makes unit/dev runs possible without Docker.
- [ ] `solver.synthesize_spec(findings) -> minimal spec` (only verified names; pins optional).
- [ ] `solver.prove(spec)` returns deterministic pass/fail derived **only** from exit codes,
      plus content hashes (spec, lockfile) + env fingerprint.
- [ ] Unit tests use a `FakeSandbox` (scripted ok/fail). 
- [ ] `@pytest.mark.integration` `DockerSandbox`: solve with network, **smoke-run with
      `--network none`, `--user`, `--read-only`, tmpfs**; verified locally against real Docker.

### Changes
- `tools/sandbox.py`: `Sandbox` protocol, `LocalSandbox`, `DockerSandbox`
  (image `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`; two-step solve/exec; net policy).
- `tools/solver.py`: spec synthesis + `prove`.
- `tests/unit/test_solver.py`, `tests/integration/test_docker_sandbox.py`.

### Success Criteria
**Inner:** `make all`. **Outer:** `make test-integration` green in CI (Docker job).
**Manual:** confirm threat model (net-off exec) by inspecting `docker run` args + a live run.

---

## Phase 5 — `report/` evidence bundle + `budget.py`

### Test Criteria (FIRST)
- [ ] `report.json` validates against a versioned schema: `schema_version`, `findings`,
      `oracle` (exit codes), `hashes`, `env`, `tool_versions`, `cost`, `provenance`, `narrative`.
- [ ] `render_markdown(report)` produces stable `report.md`; LLM text appears only under a
      clearly-labeled **"narrative"** section.
- [ ] **Anti-theater test:** every `verdict`/`status` field is sourced from an oracle exit code;
      `_selfcheck` greps the tree and fails on any LLM-authored verdict.
- [ ] `Budget` enforces token / wall-clock / attempt caps (raises `BudgetExceeded`); a `cost`
      line is always present (0 in `--no-llm`).

### Changes
- `report/schema.py`, `report/bundle.py`, `report/render.py`, `budget.py`, expand `_selfcheck.py`.
- `tests/unit/test_report.py`, `tests/unit/test_budget.py`, `tests/unit/test_selfcheck.py`.

---

## Phase 6 — `cli.py` `--no-llm` end-to-end (Pattern A deterministic)

### Test Criteria (FIRST)
- [ ] `repro-agents audit <fixture-healthy> --no-llm` → exit 0, clean bundle.
- [ ] `repro-agents audit <fixture-faulty> --no-llm` → detects undeclared dep, synthesizes spec,
      proves it (FakeSandbox in unit / Docker in integration), writes `report.json`+`report.md`.
- [ ] Exit code reflects the oracle (green→0, unrepaired→non-zero).
- [ ] `--budget` flags wired; `--out <dir>` writes the bundle; `typer` CliRunner tests pass.

### Changes
- `cli.py` (typer app + `main()`), `agents/envforensics.py` (deterministic path).
- `tests/unit/test_cli.py`, `tests/fixtures/{healthy_pkg,faulty_pkg}/`.
- `tests/integration/test_cli_docker.py` (full pipeline on Docker).

### Success Criteria — **MVP demoable here.** `make all` green; integration green; bundle on disk.

---

## Phase 7 — Agent loop scaffold (state machine + FakeModel + smolagents adapter)

### Test Criteria (FIRST)
- [ ] `Model` protocol: `propose(context) -> Proposal`. `FakeModel` returns scripted proposals.
- [ ] `loop.run(...)` cycles propose → execute oracle → read failure → tighten → emit bundle,
      converging to oracle-green or stopping at `Budget`; **verdicts still oracle-only**.
- [ ] `audit <faulty> --agent --model fake` repairs via the loop in ≤N steps.
- [ ] `smolagents_adapter` conforms to `Model` (constructs `CodeAgent`+`LiteLLMModel`); test is
      `skipif` smolagents/key absent. **No live API call in CI.**

### Changes
- `agents/models.py`, `agents/loop.py`, extend `agents/envforensics.py`, `agents/adapters/smolagents_adapter.py`.
- `tests/unit/test_loop.py`, `tests/unit/test_adapter_contract.py`.
- Docs: "Wiring a live Claude model" (set `ANTHROPIC_API_KEY`, `--model anthropic/claude-…`).

---

## Phase 8 — MkDocs Material docs + GitHub Pages + examples + polish

### Test Criteria (FIRST)
- [ ] `mkdocs build --strict` passes (no broken links/nav).
- [ ] `docs.yml` builds + deploys to Pages on push to `main`.
- [ ] `examples/walkthrough-01/` reproduces a documented audit run end-to-end.

### Changes
- `mkdocs.yml` (Material + mkdocstrings), `docs/{index,usage,architecture,security,design}.md`
  (+ link this plan), `.github/workflows/docs.yml`, README "delta vs deptry" section,
  `examples/walkthrough-01/`, `benchmarks/repro-gym/README.md` (good-first-issue framing).
- Enable Pages: `gh api -X POST repos/nitishagar/repro-agents/pages -f build_type=workflow`.

### Success Criteria — Pages live; `make all` + integration + docs all green; history is clean milestones.

---

## Testing Strategy
- **Unit** (`-m "not integration"`): pure logic, fakes/mocks, no Docker/network. The `make all` loop.
- **Integration** (`-m integration`): real Docker (sandbox oracle, full CLI) + real PyPI/deptry. CI Docker job + local.
- **Anti-theater**: `_selfcheck` + a dedicated test enforce oracle-only verdicts (doc §8).
- **Fixtures double as proto-`repro-gym`**: `healthy_pkg` (clean) + `faulty_pkg` (seeded undeclared dep).

## Security / Threat Model (`SECURITY.md`)
- All target-code execution happens in Docker, **non-root** (`--user`), **read-only rootfs**,
  **`--network none` during smoke-run** (network only during solve, to reach the package index),
  per-run resource limits, finite timeouts.
- `registry.py` refuses to emit specs containing names not verified on PyPI (anti-slopsquat).
- Verdicts are oracle-exit-code-derived only; LLM text is labeled "narrative".

## Performance / Budget
- Hard caps: tokens, wall-clock, solve attempts. Cost line in every bundle (0 under `--no-llm`).
- Docker integration tests kept to a minimal package set to bound CI wall-clock.

## References
- Research/design doc: `~/Downloads/repro-agents-project-research-doc.md` (mission, §3 evidence, §5 layout, §8 risks).
- deptry: <https://deptry.com/usage/> · smolagents: <https://huggingface.co/docs/smolagents> ·
  uv: <https://docs.astral.sh/uv/> · nbclient: <https://nbclient.readthedocs.io>.
