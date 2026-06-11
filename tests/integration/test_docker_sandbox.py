"""Integration tests for the real sandbox oracles (Phase 4).

These pull a uv Docker image and/or hit PyPI, so they are marked ``integration``
and skipped when the backend is unavailable. ``six`` is used because it has no
dependencies, keeping the runs fast.
"""

from __future__ import annotations

import shutil

import pytest

from repro_agents.tools.sandbox import DockerSandbox, LocalSandbox

pytestmark = pytest.mark.integration

_HAS_DOCKER = DockerSandbox.available()
_HAS_UV = shutil.which("uv") is not None


@pytest.mark.skipif(not _HAS_DOCKER, reason="docker is not available")
def test_docker_solve_resolves_a_package() -> None:
    result = DockerSandbox().solve(["six"])
    assert result.ok, result.log
    assert "six" in result.lock.lower()


@pytest.mark.skipif(not _HAS_DOCKER, reason="docker is not available")
def test_docker_smoke_run_imports_installed_package() -> None:
    result = DockerSandbox().smoke_run(["six"], ["six"])
    assert result.ok, result.log


@pytest.mark.skipif(not _HAS_DOCKER, reason="docker is not available")
def test_docker_smoke_run_fails_on_missing_import() -> None:
    result = DockerSandbox().smoke_run(["six"], ["definitely_not_a_module_xyz"])
    assert result.ok is False


@pytest.mark.skipif(not _HAS_UV, reason="uv is not available")
def test_local_sandbox_solve_and_smoke() -> None:
    sandbox = LocalSandbox()
    solved = sandbox.solve(["six"])
    assert solved.ok, solved.log
    smoke = sandbox.smoke_run(["six"], ["six"])
    assert smoke.ok, smoke.log
