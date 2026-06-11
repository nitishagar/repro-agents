"""Tests that the anti-theater self-check actually catches violations (Phase 5)."""

from __future__ import annotations

from pathlib import Path

from repro_agents import _selfcheck


def test_scan_flags_llm_authored_verdict(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text(
        "def grade(model):\n    verdict = model.completion\n    return verdict\n",
        encoding="utf-8",
    )
    violations = _selfcheck.scan(tmp_path)
    assert any("bad.py" in v for v in violations)


def test_scan_passes_on_oracle_derived_verdict(tmp_path: Path) -> None:
    (tmp_path / "good.py").write_text(
        "def grade(exit_code):\n    status = 'pass' if exit_code == 0 else 'fail'\n    return status\n",
        encoding="utf-8",
    )
    assert _selfcheck.scan(tmp_path) == []


def test_real_source_tree_is_clean() -> None:
    assert _selfcheck.main() == 0
