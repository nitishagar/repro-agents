"""Command-line interface: ``repro-agents audit|version``.

v0.1 ships Pattern A (environment forensics). ``audit --no-llm`` runs the fully
deterministic pipeline; the live agent loop lands in a later milestone.

Exit codes: ``0`` only when the audit verdict is ``pass`` (no reproducibility
findings). Any findings — even repairable ones — exit ``1`` so the tool is usable
as a CI gate; the evidence bundle explains the finding and the proven fix.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

from repro_agents import __version__
from repro_agents.agents.envforensics import run_environment_forensics
from repro_agents.report import Report, write_bundle
from repro_agents.report.schema import STATUS_PASS
from repro_agents.tools.sandbox import DockerSandbox, LocalSandbox, Sandbox

app = typer.Typer(
    help="Agents that rerun your science and show their receipts.",
    no_args_is_help=True,
    add_completion=False,
)


def _tool_version(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    output = (proc.stdout or proc.stderr).strip().splitlines()
    return output[0] if output else "unknown"


def _collect_tool_versions() -> dict[str, str]:
    return {
        "repro-agents": __version__,
        "python": sys.version.split()[0],
        "uv": _tool_version(["uv", "--version"]),
        "deptry": _tool_version(["deptry", "--version"]),
    }


def _make_sandbox(kind: str) -> Sandbox:
    if kind == "local":
        return LocalSandbox()
    if kind == "docker":
        if not DockerSandbox.available():
            raise typer.BadParameter(
                "Docker is not available. Start the Docker daemon, or pass --sandbox local."
            )
        return DockerSandbox()
    raise typer.BadParameter(f"unknown sandbox {kind!r}; choose 'docker' or 'local'")


def _print_summary(report: Report, json_path: Path, md_path: Path) -> None:
    typer.echo(f"repro-agents · {report.status.upper()}")
    if report.findings:
        for finding in report.findings:
            typer.echo(f"  • [{finding.kind}] {finding.name} — {finding.detail}")
    else:
        typer.echo("  no findings ✓")
    oracle = report.oracle
    typer.echo(f"  oracle proven={oracle.proven} skipped={oracle.skipped}")
    typer.echo(f"  bundle: {json_path}")
    typer.echo(f"          {md_path}")


@app.command()
def version() -> None:
    """Print the repro-agents version."""
    typer.echo(__version__)


@app.command()
def audit(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Project directory to audit."
    ),
    no_llm: bool = typer.Option(
        False, "--no-llm", help="Deterministic checks only (the only mode in v0.1)."
    ),
    sandbox: str = typer.Option("docker", "--sandbox", help="Oracle backend: docker | local."),
    python_version: str = typer.Option("3.12", "--python", help="Interpreter for the sandbox."),
    out: Path | None = typer.Option(
        None, "--out", help="Directory to write the evidence bundle (default: current directory)."
    ),
    deptry: bool = typer.Option(True, "--deptry/--no-deptry", help="Run deptry as a cross-check."),
) -> None:
    """Audit a project's environment (Pattern A) and emit an evidence bundle."""
    if not no_llm:
        typer.echo(
            "note: the live agent loop is not wired yet; running the deterministic "
            "audit. Pass --no-llm to silence this note.",
            err=True,
        )

    backend = _make_sandbox(sandbox)
    report = run_environment_forensics(
        path,
        sandbox=backend,
        python_version=python_version,
        run_deptry_enabled=deptry,
        tool_versions=_collect_tool_versions(),
    )

    json_path, md_path = write_bundle(report, out or Path.cwd())
    _print_summary(report, json_path, md_path)
    raise typer.Exit(code=0 if report.status == STATUS_PASS else 1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
