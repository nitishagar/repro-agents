"""Tests for tools/solver.py — spec synthesis + the prove() oracle loop (Phase 4).

The sandbox is faked so these tests are fully deterministic and need neither
Docker nor the network. The real DockerSandbox is exercised in tests/integration.
"""

from __future__ import annotations

from collections.abc import Sequence

from repro_agents.tools.registry import NameCheck, VerificationResult
from repro_agents.tools.sandbox import SmokeResult, SolveResult
from repro_agents.tools.solver import Proof, prove, synthesize_spec


class FakeSandbox:
    """A scripted Sandbox implementation for deterministic solver tests."""

    def __init__(
        self, *, solve_ok: bool = True, smoke_ok: bool = True, lock: str = "six==1.17.0\n"
    ) -> None:
        self.solve_ok = solve_ok
        self.smoke_ok = smoke_ok
        self.lock = lock
        self.calls: list[tuple[str, list[str]]] = []

    def solve(self, requirements: Sequence[str], *, python_version: str = "3.12") -> SolveResult:
        self.calls.append(("solve", list(requirements)))
        return SolveResult(ok=self.solve_ok, lock=self.lock, log="solve-log")

    def smoke_run(
        self, requirements: Sequence[str], imports: Sequence[str], *, python_version: str = "3.12"
    ) -> SmokeResult:
        self.calls.append(("smoke", list(imports)))
        return SmokeResult(ok=self.smoke_ok, log="smoke-log")

    def describe(self) -> dict[str, str]:
        return {"backend": "fake"}


def _verification(verified: set[str], rejected: set[str]) -> VerificationResult:
    checks = [NameCheck(n, n, True, "pypi") for n in verified]
    checks += [NameCheck(n, n, False, "pypi") for n in rejected]
    return VerificationResult(checks=checks)


def test_synthesize_spec_keeps_only_verified_sorted() -> None:
    result = _verification({"requests", "numpy"}, {"madeup_xyz"})
    assert synthesize_spec(result) == ["numpy", "requests"]


def test_prove_ok_when_solve_and_smoke_pass() -> None:
    sb = FakeSandbox(solve_ok=True, smoke_ok=True)
    proof = prove(["six"], ["six"], sandbox=sb)
    assert isinstance(proof, Proof)
    assert proof.ok is True
    assert proof.lock
    assert proof.spec_sha256 and proof.lock_sha256
    assert ("solve", ["six"]) in sb.calls
    assert ("smoke", ["six"]) in sb.calls


def test_prove_fails_and_skips_smoke_when_solve_fails() -> None:
    sb = FakeSandbox(solve_ok=False)
    proof = prove(["six"], ["six"], sandbox=sb)
    assert proof.ok is False
    assert all(kind != "smoke" for kind, _ in sb.calls)  # never smoke-run an unsolved spec


def test_prove_fails_when_smoke_fails() -> None:
    sb = FakeSandbox(solve_ok=True, smoke_ok=False)
    proof = prove(["six"], ["six"], sandbox=sb)
    assert proof.ok is False


def test_prove_spec_hash_is_order_independent() -> None:
    sb = FakeSandbox()
    p1 = prove(["b", "a"], ["a"], sandbox=sb)
    p2 = prove(["a", "b"], ["a"], sandbox=sb)
    assert p1.spec_sha256 == p2.spec_sha256


def test_empty_spec_is_trivially_proven_without_sandbox_calls() -> None:
    sb = FakeSandbox()
    proof = prove([], [], sandbox=sb)
    assert proof.ok is True
    assert proof.skipped is True
    assert sb.calls == []
