"""Shared pytest configuration."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_repo_root = Path(__file__).resolve().parents[1]
_tests_root = Path(__file__).resolve().parent
_load_env_file(_repo_root / ".env")

import sys

if str(_tests_root) not in sys.path:
    sys.path.insert(0, str(_tests_root))


pytest_plugins = ("persistence.conftest",)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: PostgreSQL integration tests (require database configuration)",
    )
