"""Agent patterns. The loop state machine lives here; adapters stay thin.

Pattern A (environment forensics) ships in v0.1. Its deterministic pipeline runs
with no LLM at all; the agent loop merely *proposes* repairs that the same
deterministic oracle grades.
"""

from __future__ import annotations
