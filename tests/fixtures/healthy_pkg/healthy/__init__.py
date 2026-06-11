"""A healthy demo package: imports only the Python standard library."""

from __future__ import annotations

import json
import pathlib


def load(path: str) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
