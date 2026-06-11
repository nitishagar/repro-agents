# Usage

## Install

```bash
# from source
git clone https://github.com/nitishagar/repro-agents && cd repro-agents
uv sync --extra dev --extra llm
```

Requires Python ≥ 3.10 (provisioned by `uv`). Docker is required for the
sandboxed solve/smoke-run; pass `--sandbox local` to use host `uv` instead (not
network-isolated — see [Security](security.md)).

## Audit a project

```bash
uv run repro-agents audit path/to/project --no-llm
```

Key options:

| Option | Meaning |
| --- | --- |
| `--no-llm` | Deterministic checks only (the default behaviour in v0.1). |
| `--sandbox docker\|local` | Oracle backend. `docker` is the secure default. |
| `--python 3.12` | Interpreter used inside the sandbox. |
| `--out DIR` | Where to write `report.json` + `report.md` (default: cwd). |
| `--deptry / --no-deptry` | Run `deptry` as a corroborating cross-check. |
| `--model anthropic/claude-sonnet-4-6` | Use the agent loop (needs `ANTHROPIC_API_KEY` and the `llm` extra). |
| `--max-tokens / --max-attempts / --max-seconds` | Hard caps for the agent loop. |

## Exit codes

- `0` — verdict is `pass` (no reproducibility findings).
- `1` — any findings (even repairable ones) or an inconclusive run, so the tool
  can gate CI. The evidence bundle explains the finding and the proven fix.

## Example

```console
$ uv run repro-agents audit tests/fixtures/faulty_pkg --no-llm --no-deptry
repro-agents · REPAIRABLE
  • [undeclared] six — imported but not declared
  oracle proven=True skipped=False
  bundle: report.json
          report.md
```

See the [walkthrough](https://github.com/nitishagar/repro-agents/tree/main/examples/walkthrough-01)
for a full bundle.
