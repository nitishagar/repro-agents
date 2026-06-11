"""Tests for budget.py — hard caps on tokens / wall-clock / attempts (Phase 5)."""

from __future__ import annotations

import pytest

from repro_agents.budget import Budget, BudgetExceeded


def test_token_cap_raises_when_exceeded() -> None:
    budget = Budget(max_tokens=100)
    budget.add_tokens(60)
    with pytest.raises(BudgetExceeded):
        budget.add_tokens(50)


def test_attempt_cap_raises_on_too_many_attempts() -> None:
    budget = Budget(max_attempts=2)
    assert budget.new_attempt() == 1
    assert budget.new_attempt() == 2
    with pytest.raises(BudgetExceeded):
        budget.new_attempt()


def test_wall_clock_cap_uses_injected_clock() -> None:
    ticks = iter([0.0, 0.5, 5.0])
    budget = Budget(max_seconds=1.0, clock=lambda: next(ticks))
    budget.start()  # t=0.0
    budget.check_time()  # t=0.5, fine
    with pytest.raises(BudgetExceeded):
        budget.check_time()  # t=5.0, exceeded


def test_unbounded_budget_never_raises() -> None:
    budget = Budget()
    budget.start()
    budget.add_tokens(10_000_000)
    budget.new_attempt()
    budget.check_time()  # no caps → no raise
