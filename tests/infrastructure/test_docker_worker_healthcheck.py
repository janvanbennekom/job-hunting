"""Worker service must not inherit Streamlit image healthcheck."""

from __future__ import annotations

from pathlib import Path


def _worker_block(compose_text: str) -> str:
    lines = compose_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith("  worker:"):
            start = index
            continue
        if start is not None and line.startswith("  ") and not line.startswith("    "):
            return "\n".join(lines[start:index])
    if start is not None:
        return "\n".join(lines[start:])
    raise AssertionError("worker service not found")


def test_prod_worker_disables_healthcheck() -> None:
    root = Path(__file__).resolve().parents[2]
    block = _worker_block(
        (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    )
    assert "healthcheck:" in block
    assert "disable: true" in block


def test_dev_worker_disables_healthcheck() -> None:
    root = Path(__file__).resolve().parents[2]
    block = _worker_block(
        (root / "docker-compose.yml").read_text(encoding="utf-8")
    )
    assert "healthcheck:" in block
    assert "disable: true" in block
