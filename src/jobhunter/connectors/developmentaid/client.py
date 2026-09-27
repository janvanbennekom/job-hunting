"""HTTP client for DevelopmentAid public frontend job APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.developmentaid.identity import (
    DEVELOPMENTAID_JOB_DETAIL_API_BASE,
    DEVELOPMENTAID_JOB_SEARCH_API,
)


@dataclass(slots=True)
class DevelopmentAidSearchPage:
    items: list[dict[str, Any]]
    total: int
    page_number: int
    page_size: int


class DevelopmentAidJobsClient:
    """
    Uses documented-style public JSON endpoints:

    - POST /api/frontend/job/search
    - GET  /api/frontend/job/{id}
    """

    def __init__(
        self,
        *,
        user_agent: str = "JobHunter/0.1 (+local; developmentaid-connector)",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def search_jobs(
        self,
        *,
        page_number: int = 1,
        page_size: int = 25,
        keyword: str | None = None,
    ) -> DevelopmentAidSearchPage:
        filter_body: dict[str, Any] = {}
        if keyword and keyword.strip():
            filter_body["keyword"] = {
                "searchedText": keyword.strip(),
                "searchedFields": [],
            }
        payload = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "filter": filter_body,
        }
        body = self._post_json(DEVELOPMENTAID_JOB_SEARCH_API, payload)
        items = list(body.get("items") or [])
        return DevelopmentAidSearchPage(
            items=items,
            total=int(body.get("total") or 0),
            page_number=page_number,
            page_size=page_size,
        )

    def get_job(self, job_id: int | str) -> dict[str, Any]:
        url = f"{DEVELOPMENTAID_JOB_DETAIL_API_BASE}/{job_id}"
        return self._get_json(url)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "User-Agent": self._user_agent,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"DevelopmentAid POST {url} failed ({exc.code}): {detail}"
            ) from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("DevelopmentAid search response must be a JSON object")
        return parsed

    def _get_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"DevelopmentAid GET {url} failed ({exc.code}): {detail}"
            ) from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("DevelopmentAid job detail response must be a JSON object")
        return parsed
