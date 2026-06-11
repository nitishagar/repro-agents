"""Schema-versioned data model for the evidence bundle (``report.json``).

The bundle is the product of every audit: findings, the oracle's verdict, content
hashes, an environment fingerprint, tool versions, a cost line, and a clearly
separated ``narrative`` field that is the *only* place LLM text may appear.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

#: Bump on any backwards-incompatible change to the bundle shape.
SCHEMA_VERSION = "1.0"

# Verdict strings. Each is derived ONLY from deterministic signals (finding counts
# + oracle exit codes), never from LLM output — see report/bundle.py.
STATUS_PASS = "pass"  # no reproducibility findings
STATUS_REPAIRABLE = "repairable"  # findings, but the oracle proved a fix
STATUS_FAIL = "fail"  # findings and the oracle could not prove a fix
STATUS_BLOCKED = "blocked"  # an unverifiable (possibly slopsquatted) name; refuse to repair
STATUS_INCOMPLETE = "incomplete"  # the oracle could not run


@dataclass
class Finding:
    kind: str  # "undeclared" | "unverified" | "unused"
    name: str
    detail: str = ""
    locations: list[str] = field(default_factory=list)


@dataclass
class OracleResult:
    proven: bool
    skipped: bool
    requirements: list[str]
    imports_checked: list[str]
    spec_sha256: str
    lock_sha256: str
    lock: str = ""


@dataclass
class CostLine:
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0


@dataclass
class Report:
    schema_version: str
    tool: str
    tool_version: str
    pattern: str
    target: str
    status: str
    findings: list[Finding]
    oracle: OracleResult
    environment: dict[str, str]
    tool_versions: dict[str, str]
    cost: CostLine = field(default_factory=CostLine)
    narrative: str = ""
    deptry: dict[str, list[str]] | None = None
    # Reserved for future provenance/attestation (e.g. sigstore); see design doc Q3.
    provenance: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
