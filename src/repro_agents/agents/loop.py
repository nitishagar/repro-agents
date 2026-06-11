"""The Pattern A agent loop: propose → verify → execute oracle → read failure → repeat.

The loop is framework-agnostic and lives in the core (adapters stay thin). It never
asserts success itself: the verdict is :class:`~repro_agents.tools.solver.Proof`,
graded by the sandbox oracle. Proposed names are passed through the same
anti-slopsquat existence check before they are ever installed, and the whole loop
is bounded by a :class:`~repro_agents.budget.Budget`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from repro_agents.agents.models import LoopContext, Model, Proposal
from repro_agents.budget import Budget, BudgetExceeded
from repro_agents.report.schema import CostLine
from repro_agents.tools.registry import PyPIClient, RegistryError
from repro_agents.tools.sandbox import Sandbox
from repro_agents.tools.solver import Proof, prove

#: Safety bound when the budget sets no explicit attempt cap (prevents infinite loops).
DEFAULT_MAX_ATTEMPTS = 6


@dataclass
class LoopResult:
    proof: Proof
    proposals: list[Proposal]
    attempts: int
    cost: CostLine


def _verify_existing(names: Iterable[str], client: PyPIClient) -> list[str]:
    """Keep only names that verify on PyPI (fail closed on inconclusive checks)."""
    safe: list[str] = []
    for name in sorted(set(names)):
        try:
            if client.exists(name):
                safe.append(name)
        except RegistryError:
            pass  # inconclusive → treat as unverified, never install it
    return safe


def run_loop(
    *,
    undeclared_imports: Sequence[str],
    model: Model,
    sandbox: Sandbox,
    budget: Budget | None = None,
    client: PyPIClient | None = None,
    python_version: str = "3.12",
    baseline: Sequence[str] | None = None,
) -> LoopResult:
    """Drive the model→oracle loop until the oracle is satisfied or the budget runs out."""
    budget = budget or Budget()
    client = client or PyPIClient()
    budget.start()

    imports = list(undeclared_imports)
    candidate = list(baseline or [])
    proposals: list[Proposal] = []
    proof = Proof(ok=False, requirements=[], imports_checked=imports, solve_log="loop did not run")
    last_error = ""

    while True:
        if budget.max_attempts is None and budget.attempts >= DEFAULT_MAX_ATTEMPTS:
            break
        try:
            attempt = budget.new_attempt()
            budget.check_time()
        except BudgetExceeded:
            break

        context = LoopContext(
            undeclared_imports=imports,
            candidate_requirements=candidate,
            last_error=last_error,
            attempt=attempt,
        )
        proposal = model.propose(context)
        proposals.append(proposal)
        try:
            budget.add_tokens(proposal.input_tokens + proposal.output_tokens)
        except BudgetExceeded:
            break

        safe = _verify_existing(proposal.requirements, client)
        candidate = safe
        if not safe:
            last_error = "no verifiable requirements were proposed"
            proof = Proof(ok=False, requirements=[], imports_checked=imports, solve_log=last_error)
            continue

        proof = prove(safe, imports, sandbox=sandbox, python_version=python_version)
        if proof.ok:
            break
        last_error = proof.smoke_log or proof.solve_log or "spec did not solve or import"

    cost = CostLine(
        input_tokens=sum(p.input_tokens for p in proposals),
        output_tokens=sum(p.output_tokens for p in proposals),
        usd=0.0,
    )
    return LoopResult(proof=proof, proposals=proposals, attempts=budget.attempts, cost=cost)
