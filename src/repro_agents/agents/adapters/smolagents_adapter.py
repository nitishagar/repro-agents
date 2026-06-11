"""smolagents adapter: a :class:`~repro_agents.agents.models.Model` backed by Claude.

Default agent runtime per the design doc. Kept deliberately thin — the loop's state
machine lives in the core. Anthropic is reached via smolagents' ``LiteLLMModel``
(install the ``llm`` extra: ``pip install 'repro-agents[llm]'``).
"""

from __future__ import annotations

import json
import os
import re

from repro_agents.agents.models import LoopContext, Proposal

_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)
_NAME_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]+")


def parse_requirements(text: str) -> list[str]:
    """Extract distribution names from a model's answer (JSON array preferred)."""
    match = _JSON_ARRAY.search(text)
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    # Fallback: dedup name-like tokens, preserving order.
    return list(dict.fromkeys(_NAME_TOKEN.findall(text)))


def build_prompt(context: LoopContext) -> str:
    parts = [
        "A scientific Python project imports modules that are not declared as "
        "dependencies. Propose the minimal set of PyPI distribution names that "
        "provide these imports.",
        f"Undeclared imports: {', '.join(context.undeclared_imports) or '(none)'}",
    ]
    if context.candidate_requirements:
        parts.append(
            f"Current candidate spec (did not work): {', '.join(context.candidate_requirements)}"
        )
    if context.last_error:
        parts.append(f"The previous attempt failed with:\n{context.last_error[:1000]}")
    parts.append(
        'Respond with ONLY a JSON array of distribution names, e.g. ["scikit-learn", "numpy"].'
    )
    return "\n\n".join(parts)


class SmolagentsModel:
    """Adapt a smolagents ``CodeAgent`` + Anthropic Claude to the ``Model`` protocol."""

    def __init__(
        self,
        *,
        model_id: str = "anthropic/claude-sonnet-4-6",
        api_key: str | None = None,
        max_steps: int = 4,
    ) -> None:
        from smolagents import CodeAgent, LiteLLMModel  # lazy: only needs the llm extra

        self._code_agent = CodeAgent
        self._llm = LiteLLMModel(
            model_id=model_id,
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )
        self._max_steps = max_steps

    def propose(self, context: LoopContext) -> Proposal:
        agent = self._code_agent(tools=[], model=self._llm, max_steps=self._max_steps)
        answer = str(agent.run(build_prompt(context)))
        requirements = parse_requirements(answer)
        input_tokens, output_tokens = _token_usage(agent)
        return Proposal(
            requirements=requirements,
            rationale=answer,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def _token_usage(agent: object) -> tuple[int, int]:
    """Best-effort token accounting; returns (0, 0) if the runtime does not expose it."""
    usage = getattr(agent, "token_usage", None) or getattr(
        getattr(agent, "monitor", None), "total_token_counts", None
    )
    try:
        if usage is not None:
            return int(getattr(usage, "input_tokens", 0)), int(getattr(usage, "output_tokens", 0))
    except (TypeError, ValueError):
        pass
    return 0, 0
