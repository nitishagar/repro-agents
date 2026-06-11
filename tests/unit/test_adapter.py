"""Tests for the smolagents adapter (Phase 7). No live API call is made."""

from __future__ import annotations

import pytest

from repro_agents.agents.adapters.smolagents_adapter import build_prompt, parse_requirements
from repro_agents.agents.models import LoopContext, Model


def test_parse_requirements_from_json_array() -> None:
    assert parse_requirements('Here you go: ["six", "scikit-learn"]') == ["six", "scikit-learn"]


def test_parse_requirements_fallback_to_tokens() -> None:
    assert parse_requirements("six requests") == ["six", "requests"]


def test_parse_requirements_dedups() -> None:
    assert parse_requirements("numpy numpy pandas") == ["numpy", "pandas"]


def test_build_prompt_mentions_imports_and_last_error() -> None:
    prompt = build_prompt(
        LoopContext(undeclared_imports=["six"], candidate_requirements=["wrong"], last_error="boom")
    )
    assert "six" in prompt and "boom" in prompt and "JSON array" in prompt


def test_adapter_conforms_to_model_protocol() -> None:
    pytest.importorskip("smolagents")
    from repro_agents.agents.adapters.smolagents_adapter import SmolagentsModel

    model = SmolagentsModel(model_id="anthropic/claude-sonnet-4-6", api_key="dummy-not-used")
    assert isinstance(model, Model)  # structural: it exposes propose()
