"""Tests for tools/deps.py — declared-dep parsing, diff, deptry cross-check (Phase 3)."""

from __future__ import annotations

from pathlib import Path

from repro_agents.tools.deps import (
    DeptryResult,
    DeptryUnavailable,
    diff,
    parse_declared,
    run_deptry,
)
from repro_agents.tools.imports import ImportInventory, Location


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _inv(*names: str) -> ImportInventory:
    inv = ImportInventory()
    for name in names:
        inv.add(name, Location(file="x.py", line=1))
    return inv


def test_parse_pyproject_dependencies_and_extras(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        """
[project]
name = "demo"
dependencies = ["requests>=2", "numpy"]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff"]
""",
    )
    declared = parse_declared(tmp_path)
    assert {"requests", "numpy", "pytest", "ruff"} <= declared.names


def test_parse_requirements_txt(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "requirements.txt",
        "# a comment\n"
        "-r other.txt\n"
        "pandas==1.5.0\n"
        "scipy ; python_version > '3.9'\n"
        "some-package[extra]>=1.0\n"
        "\n",
    )
    declared = parse_declared(tmp_path)
    assert {"pandas", "scipy", "some-package"} <= declared.names
    assert "other.txt" not in declared.names  # the -r include is not a package


def test_parse_environment_yml(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "environment.yml",
        """
name: demo
channels:
  - conda-forge
dependencies:
  - python=3.11
  - numpy=1.21
  - conda-forge::scipy
  - pip
  - pip:
    - requests>=2
    - pandas
""",
    )
    declared = parse_declared(tmp_path)
    assert {"numpy", "scipy", "requests", "pandas"} <= declared.names
    assert "python" not in declared.names  # the interpreter is not a distribution


def test_diff_reports_undeclared_and_unused() -> None:
    imports = _inv("requests", "cv2")  # cv2 → opencv-python via the override table
    declared = parse_declared_from_names({"requests", "numpy"})
    result = diff(imports, declared, installed_map={})

    assert result.undeclared == {"opencv-python"}
    assert result.unused == {"numpy"}
    assert result.used == {"requests", "opencv-python"}


def test_diff_canonicalizes_before_comparing() -> None:
    imports = _inv("sklearn")  # → scikit-learn
    declared = parse_declared_from_names({"scikit-learn"})
    result = diff(imports, declared, installed_map={})
    assert result.undeclared == set()
    assert result.unused == set()


def test_run_deptry_parses_dep001_and_dep002() -> None:
    payload = [
        {"error": {"code": "DEP001", "message": "x"}, "module": "requests"},
        {"error": {"code": "DEP002", "message": "y"}, "module": "unusedpkg"},
        {"error": {"code": "DEP003", "message": "z"}, "module": "transitive"},
    ]
    result = run_deptry(Path("."), runner=lambda _: payload)
    assert isinstance(result, DeptryResult)
    assert result.missing == {"requests"}
    assert result.unused == {"unusedpkg"}


def test_run_deptry_unavailable_returns_none() -> None:
    def runner(_: Path) -> list[dict[str, object]]:
        raise DeptryUnavailable("deptry not installed")

    assert run_deptry(Path("."), runner=runner) is None


# --- helper that builds DeclaredDeps without writing files ---
def parse_declared_from_names(names: set[str]) -> object:
    from packaging.utils import canonicalize_name

    from repro_agents.tools.deps import DeclaredDeps

    canon = {canonicalize_name(n) for n in names}
    return DeclaredDeps(names=canon, sources={n: ["<test>"] for n in canon})
