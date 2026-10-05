"""HTTP timeout wiring for source connectors."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobhunter.connectors.http_timeout import http_timeout

CONNECTOR_CLIENTS = [
    "src/jobhunter/connectors/fao/client.py",
    "src/jobhunter/connectors/developmentaid/client.py",
    "src/jobhunter/connectors/worldbank/client.py",
    "src/jobhunter/connectors/undp/client.py",
    "src/jobhunter/connectors/afdb/client.py",
    "src/jobhunter/connectors/adb/client.py",
    "src/jobhunter/connectors/ted/client.py",
    "src/jobhunter/connectors/reliefweb/client.py",
]


def test_http_timeout_returns_connect_and_read() -> None:
    connect, read = http_timeout(60.0, connect_seconds=10.0)
    assert connect == 10.0
    assert read == 60.0


@pytest.mark.parametrize("relative_path", CONNECTOR_CLIENTS)
def test_connector_clients_use_http_timeout_helper(relative_path: str) -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / relative_path).read_text(encoding="utf-8")
    assert "urlopen_with_timeouts" in source or "opener_open_with_timeouts" in source


def test_urlopen_calls_do_not_use_bare_float_timeout() -> None:
    """Guard against unbounded single-timeout urlopen in connector clients."""
    root = Path(__file__).resolve().parents[2]
    for relative_path in CONNECTOR_CLIENTS:
        text = (root / relative_path).read_text(encoding="utf-8")
        assert "timeout=self._timeout" not in text
        assert "urllib.request.urlopen(request" not in text
