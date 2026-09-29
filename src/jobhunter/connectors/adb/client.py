"""HTTP client for ADB CSRN public listing pages."""

from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar

from jobhunter.connectors.adb.identity import ADB_CSRN_LISTING_URL
from jobhunter.connectors.adb.parse import (
    AdbCsrnParseError,
    extract_next_page_tokens,
    parse_form_fields,
    parse_listing_page,
)

_DEFAULT_USER_AGENT = "JobHunter/0.1 (+adb-csrn-connector)"


@dataclass(slots=True)
class AdbCsrnListingResult:
    notices: list[dict]
    pages_fetched: int
    parse_error: str | None = None


class AdbCsrnClient:
    def __init__(
        self,
        *,
        listing_url: str = ADB_CSRN_LISTING_URL,
        user_agent: str = _DEFAULT_USER_AGENT,
        timeout_seconds: float = 90.0,
        page_delay_seconds: float = 1.0,
    ) -> None:
        self._listing_url = listing_url
        self._user_agent = user_agent
        self._timeout = timeout_seconds
        self._page_delay = page_delay_seconds
        jar = CookieJar()
        ctx = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar),
            urllib.request.HTTPSHandler(context=ctx),
        )

    def fetch_notices(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
    ) -> AdbCsrnListingResult:
        if limit <= 0:
            return AdbCsrnListingResult(notices=[], pages_fetched=0)

        html = self._get(self._listing_url)
        collected: list[dict] = []
        pages = 1

        while True:
            try:
                page_notices = [
                    notice.to_record()
                    for notice in parse_listing_page(html)
                ]
            except AdbCsrnParseError as exc:
                if collected:
                    return AdbCsrnListingResult(
                        notices=collected[:limit],
                        pages_fetched=pages,
                        parse_error=str(exc),
                    )
                raise RuntimeError(str(exc)) from exc

            if keyword and keyword.strip():
                needle = keyword.strip().lower()
                page_notices = [
                    row
                    for row in page_notices
                    if needle in (row.get("title") or "").lower()
                    or needle in (row.get("expertise") or "").lower()
                ]

            for row in page_notices:
                if len(collected) >= limit:
                    break
                collected.append(row)

            if len(collected) >= limit:
                break

            tokens = extract_next_page_tokens(html)
            if not tokens:
                break

            time.sleep(self._page_delay)
            try:
                html = self._post_next_page(html, tokens)
            except RuntimeError:
                break
            pages += 1
            if pages > 20:
                break

        if pages == 1 and not collected and ROW_MARKER_present(html):
            raise RuntimeError(
                "ADB CSRN listing page returned rows but parser produced zero notices"
            )

        return AdbCsrnListingResult(
            notices=collected[:limit], pages_fetched=pages
        )

    def _get(self, url: str) -> str:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent, "Accept": "text/html"},
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(
                f"ADB CSRN request failed ({exc.code}): {detail}"
            ) from exc

    def _post_next_page(self, current_html: str, tokens: tuple[str, str]) -> str:
        action, fields = parse_form_fields(current_html)
        post_url = self._listing_url
        if action:
            if action.startswith("/"):
                post_url = "https://selfservice.adb.org" + action
            elif action.startswith("http"):
                post_url = action
        token_a, token_b = tokens
        data = dict(fields)
        data["event"] = "goto"
        data["source"] = "atResults"
        data["_navBarSubmit"] = "goto"
        data["goto"] = token_a
        data["goto2"] = token_b
        body = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(
            post_url,
            data=body,
            method="POST",
            headers={
                "User-Agent": self._user_agent,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html",
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout) as response:
                return response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(
                f"ADB CSRN pagination failed ({exc.code}): {detail}"
            ) from exc


def ROW_MARKER_present(html: str) -> bool:
    return "atResults:mstProject:" in html
