"""Unit tests for the deterministic Pattern A pipeline (Phase 6).

Uses a fake sandbox and a fake PyPI client so the full pipeline runs with no
Docker and no network.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from repro_agents.agents.envforensics import run_environment_forensics
from repro_agents.tools.registry import PyPIClient
from repro_agents.tools.sandbox import SmokeResult, SolveResult

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class FakeSandbox:
    def __init__(self, *, solve_ok: bool = True, smoke_ok: bool = True) -> None:
        self.solve_ok = solve_ok
        self.smoke_ok = smoke_ok
        self.calls: list[str] = []

    def solve(self, requirements: Sequence[str], *, python_version: str = "3.12") -> SolveResult:
        self.calls.append("solve")
        return SolveResult(ok=self.solve_ok, lock="six==1.17.0\n", log="")

    def smoke_run(
        self, requirements: Sequence[str], imports: Sequence[str], *, python_version: str = "3.12"
    ) -> SmokeResult:
        self.calls.append("smoke")
        return SmokeResult(ok=self.smoke_ok, log="")

    def describe(self) -> dict[str, str]:
        return {"backend": "fake"}


def test_healthy_project_passes_without_touching_the_sandbox() -> None:
    sandbox = FakeSandbox()
    report = run_environment_forensics(
        FIXTURES / "healthy_pkg",
        sandbox=sandbox,
        run_deptry_enabled=False,
    )
    assert report.status == "pass"
    assert report.findings == []
    assert sandbox.calls == []  # nothing undeclared → nothing to prove


def test_faulty_project_is_repairable_when_oracle_proves_the_fix() -> None:
    sandbox = FakeSandbox(solve_ok=True, smoke_ok=True)
    client = PyPIClient(fetch=lambda name: True)  # pretend every name exists on PyPI
    report = run_environment_forensics(
        FIXTURES / "faulty_pkg",
        sandbox=sandbox,
        pypi_client=client,
        run_deptry_enabled=False,
    )
    assert report.status == "repairable"
    assert any(f.kind == "undeclared" and f.name == "six" for f in report.findings)
    assert report.oracle.proven is True
    assert "solve" in sandbox.calls and "smoke" in sandbox.calls


def test_faulty_project_fails_when_oracle_cannot_prove_fix() -> None:
    sandbox = FakeSandbox(solve_ok=False)
    client = PyPIClient(fetch=lambda name: True)
    report = run_environment_forensics(
        FIXTURES / "faulty_pkg",
        sandbox=sandbox,
        pypi_client=client,
        run_deptry_enabled=False,
    )
    assert report.status == "fail"


def test_unverifiable_dependency_is_blocked() -> None:
    sandbox = FakeSandbox()
    client = PyPIClient(fetch=lambda name: False)  # nothing verifies → slopsquat guard trips
    report = run_environment_forensics(
        FIXTURES / "faulty_pkg",
        sandbox=sandbox,
        pypi_client=client,
        run_deptry_enabled=False,
    )
    assert report.status == "blocked"
    assert sandbox.calls == []  # we refuse to even try proving an unverifiable name
