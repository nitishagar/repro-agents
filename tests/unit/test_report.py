"""Tests for report/ — schema, oracle-derived status, markdown render (Phase 5)."""

from __future__ import annotations

import json
from pathlib import Path

from repro_agents.report import build_report, write_bundle
from repro_agents.report.schema import SCHEMA_VERSION, CostLine
from repro_agents.tools.deps import DepDiff
from repro_agents.tools.registry import NameCheck, VerificationResult
from repro_agents.tools.solver import Proof


def _verification(*, rejected: set[str] | None = None) -> VerificationResult:
    checks = [NameCheck(n, n, False, "pypi") for n in (rejected or set())]
    return VerificationResult(checks=checks)


def _proof(ok: bool, *, skipped: bool = False) -> Proof:
    return Proof(
        ok=ok,
        requirements=["requests"],
        imports_checked=["requests"],
        lock="requests==2.0\n",
        spec_sha256="a" * 64,
        lock_sha256="b" * 64,
        skipped=skipped,
    )


def _build(
    diff: DepDiff, verification: VerificationResult, proof: Proof, narrative: str = ""
) -> object:
    return build_report(
        target="/tmp/demo",
        tool_version="0.1.0",
        diff=diff,
        verification=verification,
        proof=proof,
        sandbox_info={"backend": "docker"},
        tool_versions={"deptry": "0.25.1", "uv": "0.9.26"},
        narrative=narrative,
    )


def test_clean_project_passes() -> None:
    report = _build(
        DepDiff(undeclared=set(), unused=set(), used={"requests"}),
        _verification(),
        _proof(ok=True, skipped=True),
    )
    assert report.status == "pass"
    assert report.findings == []
    assert report.schema_version == SCHEMA_VERSION


def test_undeclared_but_proven_is_repairable() -> None:
    report = _build(
        DepDiff(undeclared={"requests"}, unused=set(), used={"requests"}),
        _verification(),
        _proof(ok=True),
    )
    assert report.status == "repairable"
    assert any(f.kind == "undeclared" and f.name == "requests" for f in report.findings)


def test_undeclared_and_unproven_fails() -> None:
    report = _build(
        DepDiff(undeclared={"requests"}, unused=set(), used={"requests"}),
        _verification(),
        _proof(ok=False),
    )
    assert report.status == "fail"


def test_unverifiable_name_blocks_repair() -> None:
    report = _build(
        DepDiff(undeclared={"madeup_xyz"}, unused=set(), used={"madeup_xyz"}),
        _verification(rejected={"madeup_xyz"}),
        _proof(ok=False),
    )
    assert report.status == "blocked"
    assert any(f.kind == "unverified" for f in report.findings)


def test_status_ignores_narrative_claims() -> None:
    # The Oracle Principle: a glowing LLM narrative must not flip a failing verdict.
    report = _build(
        DepDiff(undeclared={"requests"}, unused=set(), used={"requests"}),
        _verification(),
        _proof(ok=False),
        narrative="Everything reproduced perfectly! 100% success!",
    )
    assert report.status == "fail"
    assert "perfectly" in report.narrative  # narrative is preserved, just not authoritative


def test_cost_line_defaults_to_zero() -> None:
    report = _build(
        DepDiff(set(), set(), {"requests"}),
        _verification(),
        _proof(ok=True, skipped=True),
    )
    assert report.cost == CostLine(input_tokens=0, output_tokens=0, usd=0.0)


def test_write_bundle_roundtrips_json_and_renders_markdown(tmp_path: Path) -> None:
    report = _build(
        DepDiff(undeclared={"requests"}, unused={"oldpkg"}, used={"requests"}),
        _verification(),
        _proof(ok=True),
        narrative="Proposed adding requests.",
    )
    json_path, md_path = write_bundle(report, tmp_path)

    assert json_path.name == "report.json"
    assert md_path.name == "report.md"
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == SCHEMA_VERSION
    assert loaded["status"] == "repairable"

    md = md_path.read_text(encoding="utf-8")
    assert "repairable" in md.lower()
    assert "requests" in md
    # The narrative must be present but explicitly labelled as non-authoritative.
    assert "Narrative" in md and "non-authoritative" in md.lower()
