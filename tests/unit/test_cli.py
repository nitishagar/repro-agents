"""CLI surface tests (Phase 6). The healthy audit is hermetic: no Docker, no net."""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from repro_agents import __version__
from repro_agents.cli import app

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip ANSI styling so assertions don't depend on rich's color/width output."""
    return _ANSI.sub("", text)


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_audit_help_lists_no_llm_flag() -> None:
    result = runner.invoke(app, ["audit", "--help"])
    assert result.exit_code == 0
    # rich may inject ANSI styling mid-token when color is forced (e.g. in CI),
    # so strip it before checking for the flag.
    assert "--no-llm" in _plain(result.output)


def test_audit_healthy_project_passes(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "audit",
            str(FIXTURES / "healthy_pkg"),
            "--no-llm",
            "--sandbox",
            "local",
            "--no-deptry",
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    bundle = tmp_path / "report.json"
    assert bundle.exists()
    data = json.loads(bundle.read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    assert "PASS" in result.stdout
    assert (tmp_path / "report.md").exists()
