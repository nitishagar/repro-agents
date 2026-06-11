"""Map import names to PyPI distributions and verify they actually exist.

Two jobs:

1. ``import_to_distribution`` resolves a top-level import name (e.g. ``sklearn``)
   to the distribution that provides it (``scikit-learn``), using a curated
   override table plus ``importlib.metadata.packages_distributions()`` for
   whatever is installed.
2. ``verify_names`` checks that each resolved distribution exists on PyPI. This is
   the **anti-slopsquatting** gate: the solver must refuse to emit a spec that
   contains a name we could not verify. Verification **fails closed** — an
   inconclusive check (network error) is treated as *not verified*.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from importlib.metadata import packages_distributions

from packaging.utils import canonicalize_name

#: Curated import-name → distribution-name overrides for common mismatches.
IMPORT_TO_DISTRIBUTION: dict[str, str] = {
    "sklearn": "scikit-learn",
    "skimage": "scikit-image",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "yaml": "PyYAML",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "attr": "attrs",
    "OpenSSL": "pyOpenSSL",
    "serial": "pyserial",
    "Crypto": "pycryptodome",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "fitz": "PyMuPDF",
    "jwt": "PyJWT",
    "usb": "pyusb",
    "win32com": "pywin32",
    "google": "google-api-python-client",
    "cairo": "pycairo",
    "gi": "PyGObject",
}

_PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"
_USER_AGENT = "repro-agents (+https://github.com/nitishagar/repro-agents)"


class RegistryError(RuntimeError):
    """Raised when an existence check is inconclusive (e.g. a network failure)."""


def import_to_distribution(
    import_name: str,
    *,
    installed_map: Mapping[str, list[str]] | None = None,
) -> str:
    """Resolve a top-level import name to its distribution name (best effort)."""
    if import_name in IMPORT_TO_DISTRIBUTION:
        return IMPORT_TO_DISTRIBUTION[import_name]
    if installed_map is None:
        installed_map = packages_distributions()
    dists = installed_map.get(import_name)
    if dists:
        return sorted(dists)[0]
    return import_name


def _default_fetch(distribution: str, timeout: float = 10.0) -> bool:
    """Return True iff PyPI has a JSON record for ``distribution``."""
    url = _PYPI_JSON_URL.format(name=distribution)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise RegistryError(f"PyPI returned HTTP {exc.code} for {distribution!r}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RegistryError(f"could not reach PyPI for {distribution!r}: {exc}") from exc


class PyPIClient:
    """Existence checker for PyPI distributions, with an injectable fetcher + cache."""

    def __init__(
        self, fetch: Callable[[str], bool] | None = None, *, timeout: float = 10.0
    ) -> None:
        self._timeout = timeout
        self._fetch: Callable[[str], bool] = fetch or (lambda name: _default_fetch(name, timeout))
        self._cache: dict[str, bool] = {}

    def exists(self, distribution: str) -> bool:
        key = canonicalize_name(distribution)
        if key not in self._cache:
            self._cache[key] = self._fetch(distribution)
        return self._cache[key]


@dataclass(frozen=True)
class NameCheck:
    """The verification outcome for a single import name."""

    import_name: str
    distribution: str
    exists: bool
    source: str  # "allowlist" | "pypi" | "error"


@dataclass
class VerificationResult:
    """Result of verifying a set of import names against PyPI."""

    checks: list[NameCheck]
    errors: list[str] = field(default_factory=list)

    @property
    def verified(self) -> set[str]:
        """Distribution names that exist and are safe to put in a spec."""
        return {c.distribution for c in self.checks if c.exists}

    @property
    def rejected(self) -> set[str]:
        """Import names whose distribution could not be verified (fail closed)."""
        return {c.import_name for c in self.checks if not c.exists}


def verify_names(
    import_names: Iterable[str],
    *,
    client: PyPIClient | None = None,
    allowlist: Iterable[str] | None = None,
    installed_map: Mapping[str, list[str]] | None = None,
) -> VerificationResult:
    """Resolve and verify each import name, refusing anything unverifiable.

    Names on ``allowlist`` (matched by canonical distribution name) skip the network
    check. Any name whose existence check raises :class:`RegistryError` is recorded
    as *not verified* — verification fails closed.
    """
    client = client or PyPIClient()
    allow = {canonicalize_name(a) for a in (allowlist or ())}

    checks: list[NameCheck] = []
    errors: list[str] = []
    for name in sorted(import_names):
        distribution = import_to_distribution(name, installed_map=installed_map)
        if canonicalize_name(distribution) in allow:
            checks.append(NameCheck(name, distribution, True, "allowlist"))
            continue
        try:
            exists = client.exists(distribution)
            source = "pypi"
        except RegistryError as exc:
            errors.append(f"{distribution}: {exc}")
            exists = False
            source = "error"
        checks.append(NameCheck(name, distribution, exists, source))

    return VerificationResult(checks=checks, errors=errors)
