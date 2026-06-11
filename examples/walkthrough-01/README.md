# Walkthrough 01 — auditing a project with an undeclared dependency

This walkthrough audits a tiny project whose code imports `six` but never declares
it. It mirrors the most common real-world reproducibility failure: *missing
dependencies*.

The demo project is the seeded-fault fixture
[`tests/fixtures/faulty_pkg`](https://github.com/nitishagar/repro-agents/tree/main/tests/fixtures/faulty_pkg):

```python
# faulty/__init__.py
import six              # <-- imported but NOT in pyproject.toml

def is_py3() -> bool:
    return six.PY3
```

## Run it

```bash
uv run repro-agents audit tests/fixtures/faulty_pkg --no-llm --no-deptry --out /tmp/bundle
```

Expected summary:

```
repro-agents · REPAIRABLE
  • [undeclared] six — imported but not declared
  oracle proven=True skipped=False
  bundle: /tmp/bundle/report.json
          /tmp/bundle/report.md
```

Exit code is `1` (a finding is present), and the bundle records the **proven** fix.

## What the bundle proves

`report.json` (excerpt):

```json
{
  "status": "repairable",
  "findings": [{ "kind": "undeclared", "name": "six", "detail": "imported but not declared" }],
  "oracle": {
    "proven": true,
    "requirements": ["six"],
    "imports_checked": ["six"],
    "lock": "six==1.17.0\n",
    "spec_sha256": "…",
    "lock_sha256": "…"
  },
  "environment": { "sandbox": "docker", "isolation": "non-root, read-only rootfs, --network none during smoke-run" }
}
```

The verdict comes from the sandbox exit codes: `six` was verified on PyPI, the spec
solved to `six==1.17.0`, and `import six` succeeded with the network turned off.
