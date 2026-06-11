"""Parse declared dependencies, diff them against imports, cross-check with deptry.

``parse_declared`` reads ``pyproject.toml`` (``[project].dependencies`` and
``optional-dependencies``), ``requirements*.txt``, and ``environment.yml`` into a
set of canonical distribution names. ``diff`` compares those against the import
inventory (mapping import names to distributions via :mod:`registry`) to produce
*undeclared* (imported-not-declared) and *unused* (declared-not-imported) sets.

``run_deptry`` shells out to the ``deptry`` tool as a corroborating signal,
parsing its ``DEP001``/``DEP002`` violations. deptry is treated as advisory: it is
wrapped behind an injectable runner (mocked in unit tests) and degrades to ``None``
when unavailable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

from repro_agents.tools.imports import ImportInventory
from repro_agents.tools.registry import import_to_distribution

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on Python 3.10
    import tomli as tomllib

JsonPayload = list[dict[str, object]]


@dataclass
class DeclaredDeps:
    """Declared distribution names (canonical) plus where each was declared."""

    names: set[str]
    sources: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class DepDiff:
    """The difference between what a project imports and what it declares."""

    undeclared: set[str]
    unused: set[str]
    used: set[str]


@dataclass
class DeptryResult:
    """Parsed deptry findings (advisory cross-check)."""

    missing: set[str]  # DEP001 — imported but undeclared
    unused: set[str]  # DEP002 — declared but unused
    raw: JsonPayload = field(default_factory=list)


class DeptryUnavailable(RuntimeError):
    """Raised when the deptry tool cannot be located or executed."""


# --------------------------------------------------------------------------- #
# Declared-dependency parsing
# --------------------------------------------------------------------------- #
def _req_name(spec: str) -> str | None:
    try:
        return canonicalize_name(Requirement(spec).name)
    except InvalidRequirement:
        return None


def _parse_pyproject(path: Path) -> set[str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    names: set[str] = set()
    for spec in project.get("dependencies", []) or []:
        if name := _req_name(str(spec)):
            names.add(name)
    for group in (project.get("optional-dependencies", {}) or {}).values():
        for spec in group or []:
            if name := _req_name(str(spec)):
                names.add(name)
    return names


def _parse_requirements(path: Path) -> set[str]:
    names: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue  # blank, comment, or an option such as -r / -e
        if name := _req_name(line):
            names.add(name)
    return names


def _conda_name(item: str) -> str | None:
    item = item.split("#", 1)[0].strip()
    if "::" in item:
        item = item.split("::", 1)[1]
    token = ""
    for char in item:
        if char in "=<>!~ [":
            break
        token += char
    token = token.strip()
    if not token or token.lower() == "python":
        return None
    return canonicalize_name(token)


def _parse_environment_yml(path: Path) -> set[str]:
    """Best-effort extraction of declared names from a conda environment file."""
    names: set[str] = set()
    in_deps = False
    deps_indent = -1
    in_pip = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if stripped.startswith("dependencies:"):
            in_deps, deps_indent, in_pip = True, indent, False
            continue
        if not in_deps:
            continue
        if indent <= deps_indent and not stripped.startswith("-"):
            break  # a new top-level mapping key ends the dependencies block
        if not stripped.startswith("-"):
            continue

        item = stripped[1:].strip()
        if item in ("pip:", "pip") or item.endswith(":"):
            in_pip = item.startswith("pip")
            continue
        # In both the conda list and the nested pip list, the package name is the
        # leading token, so a single extractor handles both.
        name = _req_name(item) if in_pip else None
        if not name:
            name = _conda_name(item)
        if name:
            names.add(name)
    return names


def parse_declared(project_dir: Path | str) -> DeclaredDeps:
    """Collect declared distribution names from all recognised manifests."""
    root = Path(project_dir)
    sources: dict[str, list[str]] = {}

    def _record(found: Iterable[str], source: str) -> None:
        for name in found:
            sources.setdefault(name, []).append(source)

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        _record(_parse_pyproject(pyproject), "pyproject.toml")

    req_files = sorted(root.glob("requirements*.txt")) + sorted(
        (root / "requirements").glob("*.txt") if (root / "requirements").is_dir() else []
    )
    for req in req_files:
        _record(_parse_requirements(req), str(req.relative_to(root)))

    for env_name in ("environment.yml", "environment.yaml"):
        env = root / env_name
        if env.is_file():
            _record(_parse_environment_yml(env), env_name)

    return DeclaredDeps(names=set(sources), sources=sources)


# --------------------------------------------------------------------------- #
# Diff
# --------------------------------------------------------------------------- #
def diff(
    imports: ImportInventory,
    declared: DeclaredDeps,
    *,
    installed_map: dict[str, list[str]] | None = None,
) -> DepDiff:
    """Compare imported distributions against declared ones (all canonicalised)."""
    used = {
        str(canonicalize_name(import_to_distribution(name, installed_map=installed_map)))
        for name in imports.names
    }
    declared_names = {str(canonicalize_name(n)) for n in declared.names}
    return DepDiff(
        undeclared=used - declared_names,
        unused=declared_names - used,
        used=used,
    )


# --------------------------------------------------------------------------- #
# deptry cross-check
# --------------------------------------------------------------------------- #
def _default_deptry_runner(project_dir: Path) -> JsonPayload:
    executable = shutil.which("deptry")
    if executable is None:
        raise DeptryUnavailable("the `deptry` executable was not found on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "deptry.json"
        try:
            # deptry exits non-zero when it finds violations; that is expected and
            # not an error for us — we read the JSON report regardless.
            subprocess.run(
                [executable, str(project_dir), "--json-output", str(out)],
                capture_output=True,
                cwd=str(project_dir),
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeptryUnavailable(f"failed to run deptry: {exc}") from exc
        if not out.is_file():
            raise DeptryUnavailable("deptry did not produce a JSON report")
        data = json.loads(out.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise DeptryUnavailable("unexpected deptry JSON shape")
    return data


def run_deptry(
    project_dir: Path | str,
    *,
    runner: Callable[[Path], JsonPayload] | None = None,
) -> DeptryResult | None:
    """Run deptry (or an injected runner) and parse DEP001/DEP002 findings.

    Returns ``None`` if deptry is unavailable, so callers can degrade gracefully.
    """
    runner = runner or _default_deptry_runner
    try:
        payload = runner(Path(project_dir))
    except DeptryUnavailable:
        return None

    missing: set[str] = set()
    unused: set[str] = set()
    for violation in payload:
        error = violation.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        module = violation.get("module")
        if not isinstance(module, str):
            continue
        if code == "DEP001":
            missing.add(module)
        elif code == "DEP002":
            unused.add(module)
    return DeptryResult(missing=missing, unused=unused, raw=payload)
