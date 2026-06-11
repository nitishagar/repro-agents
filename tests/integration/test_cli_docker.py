"""End-to-end CLI audit on the seeded-fault fixture, using the real Docker oracle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repro_agents.cli import app
from repro_agents.tools.sandbox import DockerSandbox

pytestmark = pytest.mark.integration

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.skipif(not DockerSandbox.available(), reason="docker is not available")
def test_audit_faulty_project_repairs_and_proves_with_docker(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "audit",
            str(FIXTURES / "faulty_pkg"),
            "--no-llm",
            "--sandbox",
            "docker",
            "--no-deptry",
            "--out",
            str(tmp_path),
        ],
    )
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert data["status"] == "repairable"
    assert data["oracle"]["proven"] is True
    assert "six" in data["oracle"]["requirements"]
    # Findings present → non-zero exit so it can gate CI.
    assert result.exit_code == 1
