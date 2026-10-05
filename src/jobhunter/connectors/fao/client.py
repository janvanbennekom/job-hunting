"""HTTP client for the FAO Oracle Taleo Career Section job search API."""

from __future__ import annotations

import http.cookiejar
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.fao.identity import FAO_JOBS_ENTRY_URL
from jobhunter.connectors.http_timeout import opener_open_with_timeouts


@dataclass(slots=True)
class FaoSearchPage:
    requisition_list: list[dict[str, Any]]
    current_page: int
    page_size: int
    total_count: int


class FaoJobsClient:
    """
    Uses the public ``/careersection/rest/jobboard/searchjobs`` JSON endpoint.

    A session cookie is established by loading the public job search page first.
    """

    def __init__(
        self,
        *,
        entry_url: str = FAO_JOBS_ENTRY_URL,
        lang: str = "en",
        user_agent: str = "JobHunter/0.1 (+https://github.com/job-hunting)",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._entry_url = entry_url
        self._lang = lang
        self._user_agent = user_agent
        self._timeout = timeout_seconds
        self._portal: str | None = None
        self._cookie_jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookie_jar)
        )

    def ensure_session(self) -> None:
        if self._portal is not None:
            return
        html = self._get_text(self._entry_url_with_lang())
        match = re.search(r"portalNo:\s*'(\d+)'", html)
        if not match:
            raise RuntimeError(
                "Could not determine FAO portal number from job search page"
            )
        self._portal = match.group(1)

    def search_jobs(
        self,
        *,
        keyword: str | None = None,
        page_no: int = 1,
    ) -> FaoSearchPage:
        self.ensure_session()
        fields: dict[str, str] = {}
        if keyword and keyword.strip():
            fields["KEYWORD"] = keyword.strip()
        payload = {
            "fieldData": {"fields": fields, "valid": True},
            "filterSelectionParam": {"searchFilterSelections": []},
            "advancedSearchFiltersSelectionParam": {"searchFilterSelections": []},
            "sortingSelection": {
                "sortBySelectionParam": "3",
                "ascendingSortingOrder": "false",
            },
            "multilineEnabled": True,
            "pageNo": page_no,
        }
        url = (
            "https://jobs.fao.org/careersection/rest/jobboard/searchjobs"
            f"?lang={self._lang}&portal={self._portal}"
        )
        body = self._post_json(url, payload)
        paging = body.get("pagingData") or {}
        return FaoSearchPage(
            requisition_list=list(body.get("requisitionList") or []),
            current_page=int(paging.get("currentPageNo") or page_no),
            page_size=int(paging.get("pageSize") or 0),
            total_count=int(paging.get("totalCount") or 0),
        )

    def _entry_url_with_lang(self) -> str:
        if "lang=" in self._entry_url:
            return self._entry_url
        separator = "&" if "?" in self._entry_url else "?"
        return f"{self._entry_url}{separator}lang={self._lang}"

    def _get_text(self, url: str) -> str:
        request = urllib.request.Request(
            url, headers={"User-Agent": self._user_agent}
        )
        with opener_open_with_timeouts(
            self._opener, request, read_seconds=self._timeout
        ) as response:
            return response.read().decode("utf-8", "replace")

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "User-Agent": self._user_agent,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "tz": "GMT+00:00",
                "tzname": "UTC",
            },
        )
        try:
            with opener_open_with_timeouts(
                self._opener, request, read_seconds=self._timeout
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"FAO searchjobs request failed ({exc.code}): {detail}"
            ) from exc
