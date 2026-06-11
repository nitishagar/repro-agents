"""Smoke test that establishes a green baseline for the build target."""

from __future__ import annotations

import repro_agents


def test_version_is_exposed() -> None:
    assert repro_agents.__version__ == "0.1.0"


def test_selfcheck_passes_on_clean_tree() -> None:
    from repro_agents import _selfcheck

    assert _selfcheck.main() == 0
