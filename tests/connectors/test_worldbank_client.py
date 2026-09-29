"""Tests for World Bank procnotices client parsing."""

from __future__ import annotations

import json
from pathlib import Path

from jobhunter.connectors.worldbank.client import WorldBankProcNoticesClient


class _FixtureClient(WorldBankProcNoticesClient):
    def __init__(self, payload: dict) -> None:
        super().__init__()
        self._payload = payload

    def _get_json(self, url: str) -> dict:
        return self._payload


def test_search_notices_parses_list_payload() -> None:
    payload = json.loads(
        Path("tests/fixtures/worldbank/procnotices_sample.json").read_text(
            encoding="utf-8"
        )
    )
    client = _FixtureClient(payload)
    page = client.search_notices(rows=3, offset=0)
    assert len(page.notices) == 3
    assert page.total > 0
    assert page.notices[0]["id"]


def test_search_notices_empty_rows() -> None:
    client = _FixtureClient({"procnotices": [], "total": 0, "os": 0, "rows": 0})
    page = client.search_notices(rows=0)
    assert page.notices == []
