"""Render a :class:`Report` to human-readable Markdown (``report.md``)."""

from __future__ import annotations

from repro_agents.report.schema import Report

_STATUS_BLURB = {
    "pass": "No reproducibility findings.",
    "repairable": "Findings detected; the oracle proved a minimal fix.",
    "fail": "Findings detected; the oracle could not prove a fix.",
    "blocked": "An imported name could not be verified on PyPI; refusing to repair.",
    "incomplete": "The oracle could not run; result is inconclusive.",
}


def render_markdown(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"# repro-agents audit — `{report.status.upper()}`")
    lines.append("")
    lines.append(f"> {_STATUS_BLURB.get(report.status, '')}")
    lines.append("")
    lines.append(f"- **Target:** `{report.target}`")
    lines.append(f"- **Pattern:** {report.pattern}")
    lines.append(
        f"- **Tool:** {report.tool} {report.tool_version} (schema {report.schema_version})"
    )
    lines.append("")

    lines.append("## Findings")
    if report.findings:
        lines.append("")
        lines.append("| Kind | Name | Detail |")
        lines.append("| --- | --- | --- |")
        for finding in report.findings:
            lines.append(f"| {finding.kind} | `{finding.name}` | {finding.detail} |")
    else:
        lines.append("")
        lines.append("None. ✅")
    lines.append("")

    oracle = report.oracle
    lines.append("## Oracle proof")
    lines.append("")
    if oracle.skipped:
        lines.append("Nothing to prove (no synthesized spec).")
    else:
        lines.append(f"- **Proven:** {oracle.proven}")
        lines.append(
            f"- **Requirements:** {', '.join(f'`{r}`' for r in oracle.requirements) or '—'}"
        )
        lines.append(
            f"- **Imports checked:** {', '.join(f'`{i}`' for i in oracle.imports_checked) or '—'}"
        )
        lines.append(f"- **spec sha256:** `{oracle.spec_sha256}`")
        lines.append(f"- **lock sha256:** `{oracle.lock_sha256}`")
    lines.append("")

    lines.append("## Environment")
    lines.append("")
    for key, value in sorted(report.environment.items()):
        lines.append(f"- **{key}:** {value}")
    lines.append("")

    lines.append("## Tool versions")
    lines.append("")
    for key, value in sorted(report.tool_versions.items()):
        lines.append(f"- **{key}:** {value}")
    lines.append("")

    cost = report.cost
    lines.append("## Cost")
    lines.append("")
    lines.append(
        f"- tokens in/out: {cost.input_tokens}/{cost.output_tokens} · "
        f"estimated USD: ${cost.usd:.4f}"
    )
    lines.append("")

    if report.narrative:
        lines.append("## Narrative (LLM-generated, non-authoritative)")
        lines.append("")
        lines.append("> The text below is model narration. It is **not** the verdict — the")
        lines.append("> verdict above is derived solely from deterministic oracle exit codes.")
        lines.append("")
        lines.append(report.narrative)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
