"""Tests for tools/imports.py — the AST import inventory (Phase 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from repro_agents.tools.imports import ImportInventory, collect_imports


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_collects_third_party_top_level_names(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "analysis.py",
        "import requests\n"
        "import numpy as np\n"
        "from pandas import DataFrame\n"
        "import matplotlib.pyplot as plt\n",
    )
    inv = collect_imports(tmp_path)
    assert inv.names == {"requests", "numpy", "pandas", "matplotlib"}


def test_excludes_standard_library(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "main.py",
        "import os\nimport sys\nimport os.path\n"
        "from collections import OrderedDict\n"
        "from __future__ import annotations\n",
    )
    inv = collect_imports(tmp_path)
    assert inv.names == set()


def test_excludes_first_party_modules_and_relative_imports(tmp_path: Path) -> None:
    # A local package and a local module: imports of these must be excluded.
    _write(tmp_path, "mypkg/__init__.py", "")
    _write(tmp_path, "mypkg/util.py", "")
    _write(tmp_path, "helper.py", "")
    _write(
        tmp_path,
        "mypkg/run.py",
        "import mypkg.util\n"
        "import helper\n"
        "from . import util\n"
        "from .util import thing\n"
        "import scipy\n",
    )
    inv = collect_imports(tmp_path)
    assert inv.names == {"scipy"}


def test_handles_src_layout_first_party(tmp_path: Path) -> None:
    _write(tmp_path, "src/thepkg/__init__.py", "")
    _write(tmp_path, "src/thepkg/core.py", "import thepkg\nimport sklearn\n")
    inv = collect_imports(tmp_path)
    assert inv.names == {"sklearn"}


def test_captures_conditional_and_nested_imports(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "lazy.py",
        "def f():\n"
        "    import seaborn\n"
        "try:\n"
        "    import ujson\n"
        "except ImportError:\n"
        "    ujson = None\n",
    )
    inv = collect_imports(tmp_path)
    assert inv.names == {"seaborn", "ujson"}


def test_records_locations(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "import requests\n")
    inv = collect_imports(tmp_path)
    locs = inv.locations["requests"]
    assert locs[0].file == "a.py"
    assert locs[0].line == 1


def test_syntax_error_is_recorded_not_raised(tmp_path: Path) -> None:
    _write(tmp_path, "broken.py", "import requests\nthis is not valid python(((\n")
    _write(tmp_path, "ok.py", "import numpy\n")
    inv = collect_imports(tmp_path)
    # The good file is still scanned...
    assert "numpy" in inv.names
    # ...and the broken file is reported as an error, not a crash.
    assert any("broken.py" in err for err in inv.errors)


def test_skips_virtualenv_and_build_dirs(tmp_path: Path) -> None:
    _write(tmp_path, ".venv/lib/site.py", "import evil_should_be_ignored\n")
    _write(tmp_path, "build/x.py", "import also_ignored\n")
    _write(tmp_path, "real.py", "import requests\n")
    inv = collect_imports(tmp_path)
    assert inv.names == {"requests"}


def test_explicit_first_party_param(tmp_path: Path) -> None:
    _write(tmp_path, "x.py", "import internal_lib\nimport requests\n")
    inv = collect_imports(tmp_path, first_party={"internal_lib"})
    assert inv.names == {"requests"}


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        collect_imports(tmp_path / "does-not-exist")


def test_inventory_is_dataclass_like() -> None:
    inv = ImportInventory()
    inv.add("requests", _loc())
    assert inv.names == {"requests"}
    assert inv.locations["requests"][0].line == 7


def _loc() -> object:
    from repro_agents.tools.imports import Location

    return Location(file="f.py", line=7)
