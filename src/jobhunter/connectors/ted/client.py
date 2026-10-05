"""HTTP client for TED Search API v3."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from jobhunter.connectors.http_timeout import urlopen_with_timeouts
from dataclasses import dataclass
from datetime import date
from typing import Any

from jobhunter.connectors.ted.identity import TED_EU_SEARCH_API

_DEFAULT_FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "deadline-receipt-request",
    "description-lot",
    "links",
    "notice-type",
]

# LAND-CORE default (OR of separate FT~ predicates; Phase 17D-3).
_DEFAULT_FT_CONCEPTS: tuple[tuple[str, bool], ...] = (
    ("land administration", True),
    ("cadastre", False),
    ("cadastral", False),
    ("property registration", True),
    ("land registration", True),
    ("land registry", True),
    ("land information system", True),
    ("cadastral survey", True),
)


def _ft_predicate(term: str, *, quoted: bool) -> str:
    if quoted:
        escaped = term.replace('"', '\\"')
        return f'FT~"{escaped}"'
    return f"FT~{term}"


def _default_ft_or_group() -> str:
    parts = [
        _ft_predicate(term, quoted=quoted) for term, quoted in _DEFAULT_FT_CONCEPTS
    ]
    return "(" + " OR ".join(parts) + ")"


@dataclass(slots=True)
class TedSearchPage:
    notices: list[dict[str, Any]]
    total_notice_count: int
    page: int


class TedSearchClient:
    """POST https://api.ted.europa.eu/v3/notices/search (anonymous)."""

    def __init__(
        self,
        *,
        api_url: str = TED_EU_SEARCH_API,
        user_agent: str = "JobHunter/0.1 (+ted-eu-procurement-connector)",
        timeout_seconds: float = 90.0,
    ) -> None:
        self._api_url = api_url
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def search_notices(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
        page: int = 1,
        publication_since: date | None = None,
    ) -> TedSearchPage:
        if limit <= 0:
            return TedSearchPage(notices=[], total_notice_count=0, page=page)
        query = build_ted_expert_query(keyword=keyword, publication_since=publication_since)
        body = {
            "query": query,
            "fields": list(_DEFAULT_FIELDS),
            "limit": min(limit, 100),
            "scope": "ACTIVE",
            "paginationMode": "ITERATION",
            "page": max(1, page),
        }
        payload = self._post_json(body)
        notices_raw = payload.get("notices")
        notices: list[dict[str, Any]] = []
        if isinstance(notices_raw, list):
            notices = [item for item in notices_raw if isinstance(item, dict)]
        total = int(payload.get("totalNoticeCount") or len(notices))
        return TedSearchPage(
            notices=notices, total_notice_count=total, page=page
        )

    def _post_json(self, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self._api_url,
            data=data,
            method="POST",
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen_with_timeouts(
                request, read_seconds=self._timeout
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"TED search request failed ({exc.code}): {detail}"
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError("TED search response must be a JSON object")
        return payload


def build_ted_expert_query(
    *,
    keyword: str | None = None,
    publication_since: date | None = None,
) -> str:
    since = publication_since or date(2024, 1, 1)
    pd_filter = f"PD>={since.strftime('%Y%m%d')}"
    if keyword and keyword.strip():
        text = keyword.strip().replace('"', '\\"')
        ft = f'FT~"{text}"'
    else:
        ft = _default_ft_or_group()
    return f"{ft} AND {pd_filter} SORT BY publication-date DESC"
