"""Command-line entry point.

The full ``audit | lint-nb | verify`` pipeline is wired in a later milestone; for
now this exposes ``version`` so the installed ``repro-agents`` script resolves.
"""

from __future__ import annotations

import typer

from repro_agents import __version__

app = typer.Typer(
    help="Agents that rerun your science and show their receipts.",
    no_args_is_help=True,
    add_completion=False,
)


@app.command()
def version() -> None:
    """Print the repro-agents version."""
    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
