# Security Policy & Threat Model

`repro-agents` executes **untrusted third-party research code** in order to prove
that a dependency set solves and runs. This is inherently dangerous, so execution
is confined and the threat model is explicit.

## Threat model

The primary threat is a target project (or a maliciously crafted dependency
resolved during a solve) attempting to read host data, exfiltrate over the
network, persist, or escalate privileges during an audit.

### Mitigations (Pattern A oracle)

All target-code execution happens inside a Docker container with:

- **Non-root user** (`--user`), so the process cannot act as root even inside the
  container.
- **Read-only root filesystem** (`--read-only`) plus a small writable `tmpfs` work
  area; nothing the code writes persists.
- **No network during the smoke-run** (`--network none`). The network is enabled
  **only** during the dependency *solve* step, where the container must reach the
  package index — and even then only the index is needed.
- **Resource limits** (memory/PID caps) and **finite timeouts** so a hung or
  fork-bombing cell cannot block the host.
- **No host bind-mounts of sensitive paths.** Only the audit work directory is
  mounted.

### Anti-slopsquatting

`repro-agents` refuses to write a dependency spec containing a package name that
it has not verified exists on PyPI (or that is not on an explicit allowlist). This
prevents the agent from "repairing" a project by inventing or typo-squatting a
package name.

### Anti-theater

Reproducibility verdicts are derived **only** from deterministic oracle exit
codes. LLM-authored text is confined to a labelled `narrative` field and never
becomes a verdict. A deterministic self-check (`make security`) fails the build if
this is violated.

## Reporting a vulnerability

Please open a private security advisory on GitHub, or contact the maintainer
directly. Do not file public issues for undisclosed vulnerabilities.
