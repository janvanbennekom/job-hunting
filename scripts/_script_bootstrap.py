"""Shared path/env bootstrap for operational scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def bootstrap_repo() -> Path:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    _load_env(root / ".env")
    return root


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
