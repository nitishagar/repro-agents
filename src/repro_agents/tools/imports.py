"""AST import walk → the set of third-party top-level import names in a project.

This is the first deterministic tool of Pattern A. It answers "what does this code
*actually* import?" using only static analysis (``ast``) — no execution. Standard
library and first-party (in-repo) modules are excluded so that what remains is the
set of external distributions the project depends on.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

#: Top-level names that ship with CPython (3.10+ exposes this frozenset).
_STDLIB: frozenset[str] = frozenset(sys.stdlib_module_names)

#: Directories that never contain first-party source worth auditing.
SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        ".env",
        "env",
        "build",
        "dist",
        ".eggs",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "site-packages",
        ".ipynb_checkpoints",
    }
)


@dataclass(frozen=True)
class Location:
    """Where an import was found, relative to the project root."""

    file: str
    line: int


@dataclass
class ImportInventory:
    """Third-party import names discovered in a project, with provenance."""

    names: set[str] = field(default_factory=set)
    locations: dict[str, list[Location]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def add(self, name: str, location: Location) -> None:
        self.names.add(name)
        self.locations.setdefault(name, []).append(location)


def _top_level(module: str) -> str:
    return module.split(".", 1)[0]


def _iter_python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        yield path


def _local_module_names(root: Path) -> set[str]:
    """Top-level module/package names defined in the repo (root and ``src/``)."""
    names: set[str] = set()
    for base in (root, root / "src"):
        if not base.is_dir():
            continue
        for entry in base.iterdir():
            if entry.is_file() and entry.suffix == ".py":
                names.add(entry.stem)
            elif entry.is_dir() and (entry / "__init__.py").is_file():
                names.add(entry.name)
    return names


def collect_imports(
    project_dir: Path | str,
    *,
    first_party: Iterable[str] | None = None,
) -> ImportInventory:
    """Walk ``project_dir`` and return its third-party import inventory.

    Args:
        project_dir: Project root to scan.
        first_party: Extra top-level names to treat as first-party (excluded),
            on top of those auto-detected from the repo layout.

    Returns:
        An :class:`ImportInventory`. Syntax/decoding errors are recorded in
        ``inventory.errors`` rather than raised.

    Raises:
        NotADirectoryError: if ``project_dir`` is not a directory.
    """
    root = Path(project_dir)
    if not root.is_dir():
        raise NotADirectoryError(root)

    local = _local_module_names(root)
    if first_party:
        local |= set(first_party)

    inv = ImportInventory()
    for path in _iter_python_files(root):
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            inv.errors.append(f"{path}: {exc}")
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            inv.errors.append(f"{path}: {exc}")
            continue

        rel = str(path.relative_to(root))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _maybe_add(inv, _top_level(alias.name), local, rel, node.lineno)
            elif isinstance(node, ast.ImportFrom):
                # level > 0 means a relative import → first-party by definition.
                if node.level or node.module is None:
                    continue
                _maybe_add(inv, _top_level(node.module), local, rel, node.lineno)
    return inv


def _maybe_add(
    inv: ImportInventory,
    top: str,
    local: set[str],
    rel: str,
    lineno: int,
) -> None:
    if not top or top in _STDLIB or top in local:
        return
    inv.add(top, Location(file=rel, line=lineno))
