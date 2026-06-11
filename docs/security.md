# Security & threat model

`repro-agents` executes **untrusted third-party research code** to prove a
dependency set works. Execution is therefore confined. The full policy lives in
[`SECURITY.md`](https://github.com/nitishagar/repro-agents/blob/main/SECURITY.md);
the essentials:

- **Docker oracle**: target code runs as a **non-root** user, with a **read-only**
  root filesystem and a small writable `tmpfs`.
- **No network during the smoke-run** (`--network none`). The network is enabled
  only during the dependency *solve*, where the package index is needed.
- **Resource limits + finite timeouts** so a hung or fork-bombing cell cannot block
  the host.
- **Anti-slopsquatting**: the tool refuses to write a spec containing a package
  name it has not verified on PyPI (or allowlisted), failing closed on
  inconclusive checks.
- **Anti-theater**: verdicts derive only from oracle exit codes; LLM text lives in
  a labelled `narrative` field and a build-time self-check (`make security`) fails
  if that line is crossed.

!!! warning "`--sandbox local`"
    The `local` backend runs host `uv` directly and is **not** network-isolated.
    It exists for development and CI without Docker; the Docker backend is the
    secure oracle.
