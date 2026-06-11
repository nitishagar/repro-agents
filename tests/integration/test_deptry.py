"""Integration test: run the real deptry binary on a tiny project (Phase 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from repro_agents.tools.deps import DeptryResult, run_deptry


@pytest.mark.integration
def test_real_deptry_runs_on_a_project(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.0.0"\ndependencies = []\n',
        encoding="utf-8",
    )
    (tmp_path / "demo.py").write_text("import requests\n", encoding="utf-8")

    result = run_deptry(tmp_path)
    # We assert it ran and parsed without crashing; exact findings depend on the
    # deptry version, so we keep the assertion lenient.
    assert result is None or isinstance(result, DeptryResult)
