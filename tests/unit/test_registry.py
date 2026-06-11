"""Tests for tools/registry.py — import→dist map, PyPI existence, allowlist (Phase 2)."""

from __future__ import annotations

import pytest

from repro_agents.tools.registry import (
    PyPIClient,
    RegistryError,
    import_to_distribution,
    verify_names,
)


def test_override_table_maps_known_mismatches() -> None:
    assert import_to_distribution("sklearn") == "scikit-learn"
    assert import_to_distribution("cv2") == "opencv-python"
    assert import_to_distribution("PIL") == "pillow"
    assert import_to_distribution("yaml") == "PyYAML"
    assert import_to_distribution("bs4") == "beautifulsoup4"


def test_unknown_name_defaults_to_itself() -> None:
    assert import_to_distribution("totally_unknown_pkg", installed_map={}) == "totally_unknown_pkg"


def test_installed_map_resolves_non_override_names() -> None:
    assert import_to_distribution("foo", installed_map={"foo": ["foo-dist"]}) == "foo-dist"


def test_pypi_client_exists_true_and_false() -> None:
    client = PyPIClient(fetch=lambda name: name in {"requests", "numpy"})
    assert client.exists("requests") is True
    assert client.exists("definitely-not-a-real-package") is False


def test_pypi_client_caches_results() -> None:
    calls: list[str] = []

    def fetch(name: str) -> bool:
        calls.append(name)
        return True

    client = PyPIClient(fetch=fetch)
    client.exists("requests")
    client.exists("requests")
    assert calls.count("requests") == 1  # second lookup served from cache


def test_verify_names_separates_verified_from_rejected() -> None:
    real = {"requests", "opencv-python"}
    client = PyPIClient(fetch=lambda name: name in real)
    result = verify_names({"requests", "cv2", "made_up_xyz"}, client=client)

    assert result.verified == {"requests", "opencv-python"}
    assert result.rejected == {"made_up_xyz"}


def test_allowlist_short_circuits_existence_check() -> None:
    calls: list[str] = []

    def fetch(name: str) -> bool:
        calls.append(name)
        return False

    client = PyPIClient(fetch=fetch)
    result = verify_names({"internal_lib"}, client=client, allowlist={"internal-lib"})

    assert result.verified == {"internal_lib"}
    assert calls == []  # allowlist means we never hit the network
    assert result.checks[0].source == "allowlist"


def test_network_error_fails_closed() -> None:
    def fetch(name: str) -> bool:
        raise RegistryError("network down")

    client = PyPIClient(fetch=fetch)
    result = verify_names({"requests"}, client=client)

    # Inconclusive ≠ verified: fail closed so we never emit an unverified name.
    assert result.verified == set()
    assert result.rejected == {"requests"}
    assert result.errors


@pytest.mark.integration
def test_default_fetch_hits_real_pypi() -> None:
    client = PyPIClient()
    assert client.exists("requests") is True
    assert client.exists("repro-agents-totally-not-real-xyz-9999") is False
