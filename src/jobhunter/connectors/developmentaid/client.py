"""HTTP client for DevelopmentAid public frontend job APIs."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.http_timeout import urlopen_with_timeouts
from jobhunter.connectors.developmentaid.http_policy import (
    DevelopmentAidHttpPolicy,
    rate_limit_wait_seconds,
)
from jobhunter.connectors.developmentaid.identity import (
    DEVELOPMENTAID_JOB_DETAIL_API_BASE,
    DEVELOPMENTAID_JOB_SEARCH_API,
)

logger = logging.getLogger(__name__)

SleepFn = Callable[[float], None]


@dataclass(slots=True)
class DevelopmentAidSearchPage:
    items: list[dict[str, Any]]
    total: int
    page_number: int
    page_size: int


class DevelopmentAidRateLimitExhausted(RuntimeError):
    """Detail/search request still rate-limited after bounded retries."""

    def __init__(
        self,
        *,
        status_code: int,
        url: str,
        body: str,
        attempts: int,
    ) -> None:
        super().__init__(
            f"DevelopmentAid GET {url} failed ({status_code}) after {attempts} "
            f"attempt(s): {body[:300]}"
        )
        self.status_code = status_code
        self.url = url
        self.body = body
        self.attempts = attempts


class DevelopmentAidJobsClient:
    """
    Uses documented-style public JSON endpoints:

    - POST /api/frontend/job/search
    - GET  /api/frontend/job/{id}

    Anonymous public access (no session); rate limits apply especially to detail GETs.
    """

    def __init__(
        self,
        *,
        user_agent: str = "JobHunter/0.1 (+local; developmentaid-connector)",
        timeout_seconds: float = 60.0,
        policy: DevelopmentAidHttpPolicy | None = None,
        sleep: SleepFn | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout_seconds
        self._policy = policy or DevelopmentAidHttpPolicy()
        self._sleep = sleep if sleep is not None else _default_sleep

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
        body = self._request_json(
            "POST",
            DEVELOPMENTAID_JOB_SEARCH_API,
            payload=payload,
            retry_on_rate_limit=True,
        )
        items = list(body.get("items") or [])
        return DevelopmentAidSearchPage(
            items=items,
            total=int(body.get("total") or 0),
            page_number=page_number,
            page_size=page_size,
        )

    def get_job(self, job_id: int | str) -> dict[str, Any]:
        url = f"{DEVELOPMENTAID_JOB_DETAIL_API_BASE}/{job_id}"
        return self._request_json("GET", url, retry_on_rate_limit=True)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        payload: dict[str, Any] | None = None,
        retry_on_rate_limit: bool,
    ) -> dict[str, Any]:
        attempts = 0
        rate_limit_retries = 0
        max_retries = self._policy.max_rate_limit_retries

        while True:
            attempts += 1
            request = self._build_request(method, url, payload)
            try:
                with urlopen_with_timeouts(
                    request, read_seconds=self._timeout
                ) as response:
                    parsed = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")[:500]
                if (
                    exc.code == 429
                    and retry_on_rate_limit
                    and rate_limit_retries < max_retries
                ):
                    headers = {k: v for k, v in exc.headers.items()}
                    wait = rate_limit_wait_seconds(
                        rate_limit_retries, headers, self._policy
                    )
                    rate_limit_retries += 1
                    logger.info(
                        "DevelopmentAid: HTTP 429 on %s; retry %s/%s after %.1fs",
                        url,
                        rate_limit_retries,
                        max_retries,
                        wait,
                    )
                    self._sleep(wait)
                    continue
                if exc.code == 429:
                    raise DevelopmentAidRateLimitExhausted(
                        status_code=exc.code,
                        url=url,
                        body=body,
                        attempts=attempts,
                    ) from exc
                raise RuntimeError(
                    f"DevelopmentAid {method} {url} failed ({exc.code}): {body}"
                ) from exc

            if not isinstance(parsed, dict):
                raise RuntimeError(
                    f"DevelopmentAid {method} response must be a JSON object"
                )
            return parsed

    def _build_request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None,
    ) -> urllib.request.Request:
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }
        data = None
        if method == "POST":
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload or {}).encode("utf-8")
        return urllib.request.Request(
            url, data=data, method=method, headers=headers
        )


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)
