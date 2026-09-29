"""DevelopmentAid detail throttling and HTTP 429 handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from jobhunter.connectors.developmentaid.client import (
    DevelopmentAidJobsClient,
    DevelopmentAidRateLimitExhausted,
)
from jobhunter.connectors.developmentaid.connector import DevelopmentAidJobsConnector
from jobhunter.connectors.developmentaid.http_policy import DevelopmentAidHttpPolicy

FIXTURE = Path("tests/fixtures/developmentaid/job_search_sample.json")
DETAIL = Path("tests/fixtures/developmentaid/job_detail_900001.json")


class _RecordingClient(DevelopmentAidJobsClient):
    def __init__(self, *, responses: list[Any], sleeps: list[float]) -> None:
        super().__init__(
            policy=DevelopmentAidHttpPolicy(
                detail_interval_seconds=0.0,
                max_rate_limit_retries=2,
            ),
            sleep=sleeps.append,
        )
        self._responses = list(responses)
        self.detail_calls = 0

    def search_jobs(self, **kwargs):
        from jobhunter.connectors.developmentaid.client import DevelopmentAidSearchPage

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return DevelopmentAidSearchPage(
            items=list(payload["items"]),
            total=int(payload["total"]),
            page_number=1,
            page_size=25,
        )

    def get_job(self, job_id: int | str) -> dict[str, Any]:
        self.detail_calls += 1
        if not self._responses:
            raise AssertionError("unexpected get_job call")
        action = self._responses.pop(0)
        if action == "ok":
            return json.loads(DETAIL.read_text(encoding="utf-8"))
        if isinstance(action, DevelopmentAidRateLimitExhausted):
            raise action
        raise RuntimeError(action)


def test_sequential_detail_with_interval() -> None:
    sleeps: list[float] = []
    client = _RecordingClient(responses=["ok", "ok"], sleeps=sleeps)
    policy = DevelopmentAidHttpPolicy(detail_interval_seconds=1.5)
    connector = DevelopmentAidJobsConnector(client, policy=policy, sleep=sleeps.append)
    result = connector.fetch_jobs(limit=2, fetch_details=True)
    assert len(result.details) == 2
    assert sleeps == [1.5]  # interval before 2nd detail only


def test_client_retries_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    import urllib.error

    sleeps: list[float] = []
    detail = json.loads(DETAIL.read_text(encoding="utf-8"))
    calls = {"n": 0}

    class _Resp:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return json.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def fake_urlopen(request, timeout=0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                429,
                "Too Many Attempts",
                {"Retry-After": "2"},
                io.BytesIO(b'{"status":"error"}'),
            )
        return _Resp(detail)

    monkeypatch.setattr(
        "jobhunter.connectors.developmentaid.client.urllib.request.urlopen",
        fake_urlopen,
    )
    client = DevelopmentAidJobsClient(
        policy=DevelopmentAidHttpPolicy(max_rate_limit_retries=2),
        sleep=sleeps.append,
    )
    result = client.get_job(900001)
    assert result["id"] == 900001
    assert sleeps == [2.0]


def test_detail_failure_retains_list_mapping() -> None:
    sleeps: list[float] = []
    exhausted = DevelopmentAidRateLimitExhausted(
        status_code=429, url="http://test/job/1", body="Too Many Attempts", attempts=4
    )
    client = _RecordingClient(responses=[exhausted], sleeps=sleeps)
    connector = DevelopmentAidJobsConnector(client)
    fetch = connector.fetch_jobs(limit=1, fetch_details=True)
    mapped = connector.map_to_raw_opportunities(
        fetch, source_id="developmentaid-jobs", scan_id="scan-test-0001"
    )
    assert len(mapped.raw_opportunities) == 1
    assert mapped.raw_opportunities[0].raw_title
    assert mapped.detail_errors


def test_circuit_stops_after_consecutive_429() -> None:
    sleeps: list[float] = []
    exhausted = DevelopmentAidRateLimitExhausted(
        status_code=429, url="http://test", body="Too Many Attempts", attempts=4
    )
    client = _RecordingClient(
        responses=[exhausted, exhausted, "ok"],
        sleeps=sleeps,
    )
    policy = DevelopmentAidHttpPolicy(
        detail_interval_seconds=0.0,
        consecutive_rate_limit_stop=2,
    )
    connector = DevelopmentAidJobsConnector(client, policy=policy, sleep=sleeps.append)
    result = connector.fetch_jobs(limit=3, fetch_details=True)
    assert client.detail_calls == 2
    assert any("paused after" in err for err in result.detail_errors)


@pytest.mark.integration
def test_partial_scan_semantics_detail_only(db_session) -> None:
    from jobhunter.application.developmentaid_scan import DevelopmentAidScanService
    from jobhunter.domain.source_scan_enums import SourceScanStatus

    class _Connector:
        def fetch_jobs(self, **kwargs):
            from jobhunter.connectors.developmentaid.connector import (
                DevelopmentAidScanResult,
            )

            payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
            return DevelopmentAidScanResult(
                records=list(payload["items"]),
                details={},
                detail_errors=["job 900001 detail: HTTP 429 Too Many Attempts"],
            )

        def map_to_raw_opportunities(self, *args, **kwargs):
            return DevelopmentAidJobsConnector().map_to_raw_opportunities(
                *args, **kwargs
            )

    report = DevelopmentAidScanService(db_session, _Connector()).run_scan(
        limit=2, apply=True, run_profile_assessment=False
    )
    assert report.scan.status is SourceScanStatus.PARTIAL
    assert report.processed == 2
    assert report.failed == 0
    assert report.scan.error_summary
    assert "rate-limited" in report.scan.error_summary
