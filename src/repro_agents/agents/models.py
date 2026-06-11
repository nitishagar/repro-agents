"""Model abstraction for the agent loop.

A :class:`Model` only *proposes* a set of requirements; the deterministic oracle
decides whether the proposal is correct. :class:`FakeModel` is a scripted model for
deterministic tests; framework adapters (e.g. smolagents) live under ``adapters/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LoopContext:
    """What the loop hands the model on each step."""

    undeclared_imports: list[str]
    candidate_requirements: list[str]
    last_error: str = ""
    attempt: int = 0


@dataclass
class Proposal:
    """A model's proposed fix: distribution names to install, plus narration."""

    requirements: list[str]
    rationale: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


@runtime_checkable
class Model(Protocol):
    """Anything that can propose a fix given loop context."""

    def propose(self, context: LoopContext) -> Proposal: ...


class FakeModel:
    """A scripted model for tests: returns proposals in order, clamping to the last."""

    def __init__(self, proposals: list[Proposal]) -> None:
        if not proposals:
            raise ValueError("FakeModel needs at least one proposal")
        self._proposals = list(proposals)
        self._index = 0

    def propose(self, context: LoopContext) -> Proposal:
        proposal = self._proposals[min(self._index, len(self._proposals) - 1)]
        self._index += 1
        return proposal
