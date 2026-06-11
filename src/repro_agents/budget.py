"""Hard budgets for an audit: tokens, wall-clock, and solve attempts.

Every agent run is bounded. Exceeding any cap raises :class:`BudgetExceeded`,
which the caller turns into a clean, cost-reporting stop rather than a runaway.
The clock is injectable so the caps are deterministically testable.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    """Raised when a token / time / attempt cap is exceeded."""


@dataclass
class Budget:
    """Caps for a single audit run. ``None`` means unbounded for that dimension."""

    max_tokens: int | None = None
    max_seconds: float | None = None
    max_attempts: int | None = None
    clock: Callable[[], float] = time.monotonic

    tokens: int = 0
    attempts: int = 0
    _start: float | None = field(default=None, init=False, repr=False)

    def start(self) -> None:
        self._start = self.clock()

    def elapsed(self) -> float:
        return 0.0 if self._start is None else self.clock() - self._start

    def add_tokens(self, count: int) -> None:
        self.tokens += count
        if self.max_tokens is not None and self.tokens > self.max_tokens:
            raise BudgetExceeded(f"token budget exceeded: {self.tokens} > {self.max_tokens}")

    def new_attempt(self) -> int:
        if self.max_attempts is not None and self.attempts >= self.max_attempts:
            raise BudgetExceeded(f"attempt budget exceeded: {self.attempts} >= {self.max_attempts}")
        self.attempts += 1
        return self.attempts

    def check_time(self) -> None:
        if self.max_seconds is None:
            return
        elapsed = self.elapsed()  # one clock read; reused in the message
        if elapsed > self.max_seconds:
            raise BudgetExceeded(f"time budget exceeded: {elapsed:.1f}s > {self.max_seconds}s")
