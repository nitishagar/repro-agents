"""Pattern A — environment forensics, deterministic pipeline.

Wires the tools into a single audit: collect imports → diff against declared deps
→ verify undeclared names on PyPI → synthesize a minimal spec → prove it with the
sandbox oracle → assemble an evidence bundle. No LLM is involved here; the agent
loop (see :mod:`repro_agents.agents.loop`) only *proposes* the spec that this same
oracle grades.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from packaging.utils import canonicalize_name

from repro_agents import __version__
from repro_agents.report import Report, build_report
from repro_agents.report.schema import CostLine
from repro_agents.tools.deps import DeptryResult, JsonPayload, diff, parse_declared, run_deptry
from repro_agents.tools.imports import collect_imports
from repro_agents.tools.registry import PyPIClient, import_to_distribution, verify_names
from repro_agents.tools.sandbox import Sandbox
from repro_agents.tools.solver import prove, synthesize_spec


def run_environment_forensics(
    project_dir: Path | str,
    *,
    sandbox: Sandbox,
    python_version: str = "3.12",
    pypi_client: PyPIClient | None = None,
    deptry_runner: Callable[[Path], JsonPayload] | None = None,
    run_deptry_enabled: bool = True,
    tool_versions: dict[str, str] | None = None,
    cost: CostLine | None = None,
    narrative: str = "",
) -> Report:
    """Run the deterministic Pattern A audit and return its evidence bundle."""
    project = Path(project_dir)

    inventory = collect_imports(project)
    declared = parse_declared(project)
    declared_canon = {canonicalize_name(n) for n in declared.names}
    dep_diff = diff(inventory, declared)

    undeclared_imports = sorted(
        name
        for name in inventory.names
        if canonicalize_name(import_to_distribution(name)) not in declared_canon
    )
    verification = verify_names(undeclared_imports, client=pypi_client)
    spec = synthesize_spec(verification)
    smoke_imports = [name for name in undeclared_imports if name not in verification.rejected]
    proof = prove(spec, smoke_imports, sandbox=sandbox, python_version=python_version)

    deptry_result: DeptryResult | None = None
    if run_deptry_enabled:
        deptry_result = run_deptry(project, runner=deptry_runner)

    return build_report(
        target=str(project),
        tool_version=__version__,
        diff=dep_diff,
        verification=verification,
        proof=proof,
        sandbox_info=sandbox.describe(),
        tool_versions=tool_versions or {},
        cost=cost,
        deptry_result=deptry_result,
        narrative=narrative,
    )
