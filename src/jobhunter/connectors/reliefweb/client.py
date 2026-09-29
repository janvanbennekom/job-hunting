"""HTTP client for ReliefWeb Jobs API v2."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.reliefweb.identity import RELIEFWEB_JOBS_API_BASE


class ReliefWebApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(slots=True)
class ReliefWebJobsPage:
    jobs: list[dict[str, Any]]
    total_count: int
    offset: int


class ReliefWebJobsClient:
    """
    Documented read-only API (requires pre-approved ``appname`` query parameter).

    See https://apidoc.reliefweb.int/
    """

    def __init__(
        self,
        *,
        appname: str,
        api_base: str = RELIEFWEB_JOBS_API_BASE,
        user_agent: str = "JobHunter/0.1 (+reliefweb-jobs-connector)",
        timeout_seconds: float = 60.0,
    ) -> None:
        appname = (appname or "").strip()
        if not appname:
            raise ValueError("ReliefWeb API appname is required")
        self._appname = appname
        self._api_base = api_base
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def search_jobs(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> ReliefWebJobsPage:
        if limit <= 0:
            return ReliefWebJobsPage(jobs=[], total_count=0, offset=offset)
        body: dict[str, Any] = {
            "limit": min(limit, 100),
            "offset": max(0, offset),
            "preset": "latest",
        }
        if keyword and keyword.strip():
            body["query"] = {
                "value": keyword.strip(),
                "operator": "AND",
            }
        url = f"{self._api_base}?{urllib.parse.urlencode({'appname': self._appname})}"
        payload = self._post_json(url, body)
        data = payload.get("data")
        jobs: list[dict[str, Any]] = []
        if isinstance(data, list):
            jobs = [item for item in data if isinstance(item, dict)]
        total = int(payload.get("totalCount") or len(jobs))
        return ReliefWebJobsPage(jobs=jobs, total_count=total, offset=offset)

    def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise ReliefWebApiError(
                f"ReliefWeb jobs request failed ({exc.code}): {detail}",
                status_code=exc.code,
            ) from exc
        if not isinstance(payload, dict):
            raise ReliefWebApiError("ReliefWeb jobs response must be a JSON object")
        return payload
