"""Assemble a :class:`Report` and write the evidence bundle to disk.

The status (verdict) is computed **here**, from deterministic signals only:
the finding counts and the oracle's exit-code-derived ``proven`` flag. The LLM's
``narrative`` is carried through untouched and never consulted for the verdict.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

from repro_agents.report.render import render_markdown
from repro_agents.report.schema import (
    SCHEMA_VERSION,
    STATUS_BLOCKED,
    STATUS_FAIL,
    STATUS_INCOMPLETE,
    STATUS_PASS,
    STATUS_REPAIRABLE,
    CostLine,
    Finding,
    OracleResult,
    Report,
)
from repro_agents.tools.deps import DepDiff, DeptryResult
from repro_agents.tools.registry import VerificationResult
from repro_agents.tools.solver import Proof

PATTERN = "environment-forensics"


def _findings(diff: DepDiff, verification: VerificationResult) -> list[Finding]:
    findings: list[Finding] = []
    for name in sorted(diff.undeclared):
        findings.append(Finding(kind="undeclared", name=name, detail="imported but not declared"))
    for name in sorted(verification.rejected):
        findings.append(
            Finding(
                kind="unverified", name=name, detail="could not verify on PyPI (anti-slopsquat)"
            )
        )
    for name in sorted(diff.unused):
        findings.append(
            Finding(kind="unused", name=name, detail="declared but not imported (advisory)")
        )
    return findings


def _status(diff: DepDiff, verification: VerificationResult, proof: Proof) -> str:
    if verification.rejected:
        return STATUS_BLOCKED  # an unverifiable name: refuse to repair (slopsquat risk)
    if not diff.undeclared:
        return STATUS_PASS
    if proof.skipped:
        return STATUS_INCOMPLETE
    return STATUS_REPAIRABLE if proof.ok else STATUS_FAIL


def build_report(
    *,
    target: str,
    tool_version: str,
    diff: DepDiff,
    verification: VerificationResult,
    proof: Proof,
    sandbox_info: dict[str, str],
    tool_versions: dict[str, str],
    cost: CostLine | None = None,
    narrative: str = "",
    deptry_result: DeptryResult | None = None,
) -> Report:
    environment = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "sandbox": sandbox_info.get("backend", "unknown"),
        "isolation": sandbox_info.get("isolation", ""),
    }
    deptry = (
        {"missing": sorted(deptry_result.missing), "unused": sorted(deptry_result.unused)}
        if deptry_result is not None
        else None
    )
    return Report(
        schema_version=SCHEMA_VERSION,
        tool="repro-agents",
        tool_version=tool_version,
        pattern=PATTERN,
        target=target,
        status=_status(diff, verification, proof),
        findings=_findings(diff, verification),
        oracle=OracleResult(
            proven=proof.ok,
            skipped=proof.skipped,
            requirements=proof.requirements,
            imports_checked=proof.imports_checked,
            spec_sha256=proof.spec_sha256,
            lock_sha256=proof.lock_sha256,
            lock=proof.lock,
        ),
        environment=environment,
        tool_versions=tool_versions,
        cost=cost or CostLine(),
        narrative=narrative,
        deptry=deptry,
    )


def write_bundle(report: Report, out_dir: Path | str) -> tuple[Path, Path]:
    """Write ``report.json`` + ``report.md`` into ``out_dir``; return their paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "report.json"
    md_path = out / "report.md"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path
