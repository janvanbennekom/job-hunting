"""HTTP client for AfDB consultant vacancy RSS and detail pages."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.afdb.detail import AfdbDetailPage, parse_afdb_detail_html
from jobhunter.connectors.afdb.identity import AFDB_CONSULTANTS_RSS_URL
from jobhunter.connectors.rss_feed import parse_rss_items


@dataclass(slots=True)
class AfdbFeedPage:
    items: list[dict[str, Any]]


class AfdbConsultantsClient:
    """
    Official consultants RSS feed (requires a descriptive User-Agent; bare
    urllib default may receive HTTP 403).
    """

    def __init__(
        self,
        *,
        feed_url: str = AFDB_CONSULTANTS_RSS_URL,
        user_agent: str = (
            "Mozilla/5.0 (compatible; JobHunter/0.1; +afdb-consultants-connector)"
        ),
        timeout_seconds: float = 60.0,
    ) -> None:
        self._feed_url = feed_url
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def fetch_feed(self) -> AfdbFeedPage:
        request = urllib.request.Request(
            self._feed_url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/rss+xml, application/xml, */*",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"AfDB RSS request failed ({exc.code}): {detail}"
            ) from exc
        return AfdbFeedPage(items=parse_rss_items(payload))

    def fetch_detail(self, url: str) -> AfdbDetailPage:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent, "Accept": "text/html, */*"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                html = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"AfDB detail request failed ({exc.code}): {detail}"
            ) from exc
        return parse_afdb_detail_html(html)
