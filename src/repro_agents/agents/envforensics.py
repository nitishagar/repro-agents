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
from repro_agents.agents.loop import run_loop
from repro_agents.agents.models import Model
from repro_agents.budget import Budget
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
    model: Model | None = None,
    budget: Budget | None = None,
) -> Report:
    """Run the Pattern A audit and return its evidence bundle.

    With ``model=None`` the audit is fully deterministic. With a ``model`` it runs
    the agent loop (proposals graded by the same oracle); the verdict still comes
    only from oracle exit codes.
    """
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

    if model is None:
        proof = prove(spec, smoke_imports, sandbox=sandbox, python_version=python_version)
    else:
        loop = run_loop(
            undeclared_imports=smoke_imports,
            model=model,
            sandbox=sandbox,
            budget=budget,
            client=pypi_client,
            python_version=python_version,
            baseline=spec,
        )
        proof = loop.proof
        cost = cost or loop.cost
        joined = "\n\n".join(p.rationale for p in loop.proposals if p.rationale)
        narrative = narrative or joined

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
