# repro-agents build target — the inner-loop backpressure mechanism.
# After every code change, run `make all`. Resolve every failure before proceeding.

.DEFAULT_GOAL := all
.PHONY: install build lint format typecheck test test-integration security all docs clean

install:  ## Create the environment and install dev + llm extras.
	uv sync --extra dev --extra llm

build:  ## Build sdist + wheel.
	uv build

lint:  ## Static lint + format check.
	uv run ruff check .
	uv run ruff format --check .

format:  ## Auto-fix lint + format.
	uv run ruff check --fix .
	uv run ruff format .

typecheck:  ## Static type check.
	uv run mypy src

test:  ## Fast, deterministic unit tests (no Docker / no network).
	uv run pytest -m "not integration" -q

test-integration:  ## Docker-backed oracle + network tests.
	uv run pytest -m integration -q

security:  ## Dependency CVE scan + anti-theater self-check (Oracle Principle).
	-uv run pip-audit
	uv run python -m repro_agents._selfcheck

all: lint typecheck test security  ## The inner loop. Run after EVERY change.

docs:  ## Build the documentation site (strict).
	uv run mkdocs build --strict

clean:
	rm -rf dist build site .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
