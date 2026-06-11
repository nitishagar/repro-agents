"""Evidence-bundle assembly and rendering."""

from __future__ import annotations

from repro_agents.report.bundle import build_report, write_bundle
from repro_agents.report.render import render_markdown
from repro_agents.report.schema import (
    SCHEMA_VERSION,
    CostLine,
    Finding,
    OracleResult,
    Report,
)

__all__ = [
    "SCHEMA_VERSION",
    "CostLine",
    "Finding",
    "OracleResult",
    "Report",
    "build_report",
    "render_markdown",
    "write_bundle",
]
