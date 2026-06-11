"""Deterministic, LLM-free, individually testable tools.

Each tool is a plain Python function (or small class) that an agent can call. The
oracle that grades reproducibility claims lives here, never in the LLM.
"""

from __future__ import annotations
