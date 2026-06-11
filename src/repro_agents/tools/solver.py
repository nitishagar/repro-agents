"""Synthesize a minimal dependency spec and *prove* it with the sandbox oracle.

The loop is deliberately tiny and deterministic: build a spec from verified
distribution names, ask the sandbox to ``solve`` it, and — only if that
succeeds — ask it to ``smoke_run`` the imports. The resulting :class:`Proof`'s
``ok`` flag is derived solely from sandbox exit codes (the Oracle Principle).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field

from repro_agents.tools.registry import VerificationResult
from repro_agents.tools.sandbox import Sandbox


@dataclass
class Proof:
    """Evidence that a synthesized spec solves and smoke-runs (or why it didn't)."""

    ok: bool
    requirements: list[str]
    imports_checked: list[str]
    lock: str = ""
    solve_log: str = ""
    smoke_log: str = ""
    spec_sha256: str = ""
    lock_sha256: str = ""
    skipped: bool = False
    extra: dict[str, str] = field(default_factory=dict)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def synthesize_spec(verification: VerificationResult) -> list[str]:
    """The minimal spec: every verified distribution name, sorted. Nothing else."""
    return sorted(verification.verified)


def prove(
    requirements: Sequence[str],
    imports: Sequence[str],
    *,
    sandbox: Sandbox,
    python_version: str = "3.12",
) -> Proof:
    """Run the deterministic solve → smoke-run oracle over a spec."""
    reqs = sorted(set(requirements))
    imps = sorted(set(imports))
    spec_hash = _sha256("\n".join(reqs))

    if not reqs:
        # Nothing to install means nothing to prove — trivially satisfied.
        return Proof(
            ok=True,
            requirements=reqs,
            imports_checked=imps,
            spec_sha256=spec_hash,
            skipped=True,
        )

    solve = sandbox.solve(reqs, python_version=python_version)
    if not solve.ok:
        return Proof(
            ok=False,
            requirements=reqs,
            imports_checked=imps,
            lock=solve.lock,
            solve_log=solve.log,
            spec_sha256=spec_hash,
            lock_sha256=_sha256(solve.lock),
        )

    smoke = sandbox.smoke_run(reqs, imps, python_version=python_version)
    return Proof(
        ok=solve.ok and smoke.ok,
        requirements=reqs,
        imports_checked=imps,
        lock=solve.lock,
        solve_log=solve.log,
        smoke_log=smoke.log,
        spec_sha256=spec_hash,
        lock_sha256=_sha256(solve.lock),
    )
