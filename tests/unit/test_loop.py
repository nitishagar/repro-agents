"""Tests for the agent loop state machine (Phase 7), driven by a fake model.

The loop only *proposes*; the deterministic oracle (sandbox) grades. Verdicts stay
oracle-derived. No LLM and no Docker are involved here.
"""

from __future__ import annotations

from collections.abc import Sequence

from repro_agents.agents.loop import run_loop
from repro_agents.agents.models import FakeModel, Proposal
from repro_agents.budget import Budget
from repro_agents.tools.registry import PyPIClient
from repro_agents.tools.sandbox import SmokeResult, SolveResult


class ConditionalSandbox:
    """Solve always succeeds; smoke-run succeeds only if `good` is in the spec."""

    def __init__(self, good: str = "six") -> None:
        self.good = good
        self.solve_calls = 0
        self.smoke_calls = 0

    def solve(self, requirements: Sequence[str], *, python_version: str = "3.12") -> SolveResult:
        self.solve_calls += 1
        return SolveResult(ok=True, lock="\n".join(requirements) + "\n", log="")

    def smoke_run(
        self, requirements: Sequence[str], imports: Sequence[str], *, python_version: str = "3.12"
    ) -> SmokeResult:
        self.smoke_calls += 1
        ok = self.good in requirements
        return SmokeResult(ok=ok, log="" if ok else "ModuleNotFoundError")

    def describe(self) -> dict[str, str]:
        return {"backend": "fake"}


def _client() -> PyPIClient:
    # Everything verifies except the literal name "madeup".
    return PyPIClient(fetch=lambda name: name != "madeup")


def test_loop_converges_after_a_wrong_then_right_proposal() -> None:
    model = FakeModel([Proposal(["wrongpkg"]), Proposal(["six"])])
    sandbox = ConditionalSandbox(good="six")
    result = run_loop(
        undeclared_imports=["six"],
        model=model,
        sandbox=sandbox,
        budget=Budget(max_attempts=5),
        client=_client(),
    )
    assert result.proof.ok is True
    assert result.attempts == 2
    assert result.proof.requirements == ["six"]


def test_loop_stops_at_attempt_budget_when_never_solved() -> None:
    model = FakeModel([Proposal(["wrongpkg"])])  # always the same wrong answer
    sandbox = ConditionalSandbox(good="six")
    result = run_loop(
        undeclared_imports=["six"],
        model=model,
        sandbox=sandbox,
        budget=Budget(max_attempts=3),
        client=_client(),
    )
    assert result.proof.ok is False
    assert result.attempts == 3
    assert len(result.proposals) == 3


def test_loop_refuses_unverifiable_names_without_proving() -> None:
    model = FakeModel([Proposal(["madeup"])])
    sandbox = ConditionalSandbox(good="six")
    result = run_loop(
        undeclared_imports=["madeup_mod"],
        model=model,
        sandbox=sandbox,
        budget=Budget(max_attempts=1),
        client=_client(),
    )
    assert result.proof.ok is False
    assert sandbox.solve_calls == 0  # never tried to prove an unverifiable name


def test_loop_charges_token_budget_and_reports_cost() -> None:
    model = FakeModel([Proposal(["six"], input_tokens=40, output_tokens=10)])
    sandbox = ConditionalSandbox(good="six")
    result = run_loop(
        undeclared_imports=["six"],
        model=model,
        sandbox=sandbox,
        budget=Budget(max_tokens=1000),
        client=_client(),
    )
    assert result.cost.input_tokens == 40
    assert result.cost.output_tokens == 10


def test_loop_stops_when_token_budget_exceeded() -> None:
    model = FakeModel([Proposal(["six"], input_tokens=100)])
    sandbox = ConditionalSandbox(good="six")
    result = run_loop(
        undeclared_imports=["six"],
        model=model,
        sandbox=sandbox,
        budget=Budget(max_tokens=50),
        client=_client(),
    )
    # The single over-budget proposal is recorded, but the loop stops before proving.
    assert result.proof.ok is False
    assert sandbox.solve_calls == 0
