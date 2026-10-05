"""HTTP client for UNDP official vacancy RSS feeds."""

from __future__ import annotations

import urllib.error
import urllib.request

from jobhunter.connectors.http_timeout import urlopen_with_timeouts
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.rss_feed import parse_rss_items
from jobhunter.connectors.undp.identity import UNDP_JOBS_ALL_VACANCIES_RSS


@dataclass(slots=True)
class UndpFeedPage:
    items: list[dict[str, Any]]


class UndpJobsClient:
    """
    Uses the official all-vacancies RSS feed (RSS 0.91) documented at
    jobs.undp.org — stable vacancy links include Oracle requisition ids.
    """

    def __init__(
        self,
        *,
        feed_url: str = UNDP_JOBS_ALL_VACANCIES_RSS,
        user_agent: str = "JobHunter/0.1 (+undp-jobs-connector)",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._feed_url = feed_url
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def fetch_feed(self) -> UndpFeedPage:
        request = urllib.request.Request(
            self._feed_url,
            headers={"User-Agent": self._user_agent, "Accept": "application/rss+xml, */*"},
        )
        try:
            with urlopen_with_timeouts(
                request, read_seconds=self._timeout
            ) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"UNDP RSS request failed ({exc.code}): {detail}"
            ) from exc
        return UndpFeedPage(items=parse_rss_items(payload))
