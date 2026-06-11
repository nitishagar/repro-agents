"""Deterministic anti-theater guard (Oracle Principle; design doc §8).

This module is run as part of ``make security`` (``python -m repro_agents._selfcheck``).
It fails with a non-zero exit code if it finds evidence that a reproducibility
*verdict* was authored by an LLM rather than derived from a deterministic oracle
exit code. The guard is intentionally simple and grep-like so it stays fast and
auditable.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent

# A verdict/status/`reproduced` field must never be assigned directly from LLM
# output. LLM text belongs only in a clearly labelled ``narrative`` field.
_FORBIDDEN = [
    re.compile(
        r"\b(verdict|reproduced|is_reproducible|status)\b\s*=\s*[^=].*"
        r"\b(llm|model|completion|agent_text|narrative|response\.text)\b",
        re.IGNORECASE,
    ),
]


def scan(root: Path) -> list[str]:
    """Return a list of ``path:line: text`` violations found under ``root``."""
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "_selfcheck.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(pat.search(line) for pat in _FORBIDDEN):
                violations.append(f"{path}:{lineno}: {line.strip()}")
    return violations


def main() -> int:
    violations = scan(SRC_ROOT)
    if violations:
        print("Anti-theater self-check FAILED — LLM-authored verdict detected:")
        for v in violations:
            print(f"  {v}")
        return 1
    print("Anti-theater self-check passed: no LLM-authored verdicts found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
