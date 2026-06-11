"""Sandboxes that solve a dependency spec and smoke-run it — the Pattern A oracle.

A :class:`Sandbox` exposes two deterministic primitives whose **exit codes** are
the only thing that grades a reproducibility claim:

- ``solve``: resolve a set of requirements to a pinned lockfile (network on).
- ``smoke_run``: install the requirements and ``import`` them (network OFF during
  the import step).

:class:`DockerSandbox` is the secure oracle: it runs as a non-root user, with a
read-only root filesystem and **no network** during the smoke-run (see
``SECURITY.md``). :class:`LocalSandbox` uses host ``uv`` directly; it is a
convenience/fallback backend and is **not** network-isolated.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

_DEFAULT_IMAGE = "ghcr.io/astral-sh/uv:python{python}-bookworm-slim"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class StepResult:
    """The outcome of a single subprocess/container invocation."""

    ok: bool
    returncode: int
    stdout: str
    stderr: str


@dataclass
class SolveResult:
    ok: bool
    lock: str
    log: str


@dataclass
class SmokeResult:
    ok: bool
    log: str


@runtime_checkable
class Sandbox(Protocol):
    """Structural type for the oracle backends."""

    def solve(self, requirements: Sequence[str], *, python_version: str) -> SolveResult: ...

    def smoke_run(
        self, requirements: Sequence[str], imports: Sequence[str], *, python_version: str
    ) -> SmokeResult: ...

    def describe(self) -> dict[str, str]: ...


class DockerUnavailable(RuntimeError):
    """Raised when the Docker backend cannot be used."""


def _import_code(imports: Sequence[str]) -> str:
    """Build a ``python -c`` body that imports each (validated) module name."""
    statements = [f"import {name}" for name in imports if _IDENTIFIER.match(name)]
    return "; ".join(statements) if statements else "pass"


def _combine(*steps: StepResult) -> str:
    return "\n".join(f"{s.stdout}{s.stderr}".strip() for s in steps).strip()


class DockerSandbox:
    """Rootless Docker oracle: non-root, read-only rootfs, network off on execute."""

    def __init__(
        self,
        *,
        image_template: str = _DEFAULT_IMAGE,
        timeout: int = 300,
        memory: str = "2g",
        pids_limit: int = 512,
    ) -> None:
        self._image_template = image_template
        self._timeout = timeout
        self._memory = memory
        self._pids_limit = pids_limit
        self._uid = os.getuid()
        self._gid = os.getgid()

    @staticmethod
    def available() -> bool:
        """True iff the docker CLI is installed and the daemon is reachable."""
        if shutil.which("docker") is None:
            return False
        try:
            proc = subprocess.run(["docker", "info"], capture_output=True, timeout=20, check=False)
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0

    def _image(self, python_version: str) -> str:
        return self._image_template.format(python=python_version)

    def _run(self, work: str, cmd: list[str], *, network: str, python_version: str) -> StepResult:
        base = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{work}:/work",
            "-w",
            "/work",
            "-e",
            "HOME=/work",
            "-e",
            "UV_CACHE_DIR=/work/.cache",
            "--user",
            f"{self._uid}:{self._gid}",
            "--memory",
            self._memory,
            "--pids-limit",
            str(self._pids_limit),
        ]
        if network == "none":
            base += ["--network", "none", "--read-only", "--tmpfs", "/tmp"]
        full = [*base, self._image(python_version), *cmd]
        try:
            proc = subprocess.run(
                full, capture_output=True, text=True, timeout=self._timeout, check=False
            )
        except FileNotFoundError as exc:
            raise DockerUnavailable("the `docker` executable was not found") from exc
        except subprocess.TimeoutExpired:
            return StepResult(False, 124, "", f"timed out after {self._timeout}s")
        return StepResult(proc.returncode == 0, proc.returncode, proc.stdout, proc.stderr)

    def solve(self, requirements: Sequence[str], *, python_version: str = "3.12") -> SolveResult:
        with tempfile.TemporaryDirectory() as work:
            Path(work, "requirements.in").write_text(
                "\n".join(requirements) + "\n", encoding="utf-8"
            )
            step = self._run(
                work,
                [
                    "uv",
                    "pip",
                    "compile",
                    "/work/requirements.in",
                    "-o",
                    "/work/requirements.txt",
                    "--quiet",
                ],
                network="default",
                python_version=python_version,
            )
            lock_path = Path(work, "requirements.txt")
            lock = lock_path.read_text(encoding="utf-8") if lock_path.is_file() else ""
            return SolveResult(ok=step.ok, lock=lock, log=_combine(step))

    def smoke_run(
        self, requirements: Sequence[str], imports: Sequence[str], *, python_version: str = "3.12"
    ) -> SmokeResult:
        with tempfile.TemporaryDirectory() as work:
            install_cmd = (
                "uv venv /work/.venv && uv pip install --python /work/.venv/bin/python "
                + " ".join(shlex.quote(r) for r in requirements)
            )
            install = self._run(
                work, ["sh", "-c", install_cmd], network="default", python_version=python_version
            )
            if not install.ok:
                return SmokeResult(ok=False, log=_combine(install))
            run = self._run(
                work,
                ["/work/.venv/bin/python", "-c", _import_code(imports)],
                network="none",  # the smoke-run executes target imports with NO network
                python_version=python_version,
            )
            return SmokeResult(ok=run.ok, log=_combine(install, run))

    def describe(self) -> dict[str, str]:
        return {
            "backend": "docker",
            "image_template": self._image_template,
            "isolation": "non-root, read-only rootfs, --network none during smoke-run",
        }


class LocalSandbox:
    """Host-``uv`` backend. Convenience/fallback only — NOT network-isolated."""

    def __init__(self, *, timeout: int = 300) -> None:
        self._timeout = timeout

    def _run(self, cmd: list[str]) -> StepResult:
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout, check=False
            )
        except subprocess.TimeoutExpired:
            return StepResult(False, 124, "", f"timed out after {self._timeout}s")
        return StepResult(proc.returncode == 0, proc.returncode, proc.stdout, proc.stderr)

    def solve(self, requirements: Sequence[str], *, python_version: str = "3.12") -> SolveResult:
        with tempfile.TemporaryDirectory() as work:
            req_in = Path(work, "requirements.in")
            req_in.write_text("\n".join(requirements) + "\n", encoding="utf-8")
            out = Path(work, "requirements.txt")
            step = self._run(
                [
                    "uv",
                    "pip",
                    "compile",
                    str(req_in),
                    "-o",
                    str(out),
                    "--quiet",
                    "--python-version",
                    python_version,
                ]
            )
            lock = out.read_text(encoding="utf-8") if out.is_file() else ""
            return SolveResult(ok=step.ok, lock=lock, log=_combine(step))

    def smoke_run(
        self, requirements: Sequence[str], imports: Sequence[str], *, python_version: str = "3.12"
    ) -> SmokeResult:
        with tempfile.TemporaryDirectory() as work:
            venv = Path(work, ".venv")
            created = self._run(["uv", "venv", str(venv), "--python", python_version])
            if not created.ok:
                return SmokeResult(ok=False, log=_combine(created))
            python = venv / "bin" / "python"
            install = self._run(["uv", "pip", "install", "--python", str(python), *requirements])
            if not install.ok:
                return SmokeResult(ok=False, log=_combine(install))
            run = self._run([str(python), "-c", _import_code(imports)])
            return SmokeResult(ok=run.ok, log=_combine(install, run))

    def describe(self) -> dict[str, str]:
        return {"backend": "local", "isolation": "NONE (host uv) — not the secure oracle"}
