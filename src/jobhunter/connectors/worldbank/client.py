"""HTTP client for World Bank procurement notices JSON API."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from jobhunter.connectors.worldbank.identity import WORLDBANK_PROC_NOTICES_API


@dataclass(slots=True)
class WorldBankSearchPage:
    notices: list[dict[str, Any]]
    offset: int
    rows: int
    total: int


class WorldBankProcNoticesClient:
    """
    Uses the public documented endpoint::

        GET https://search.worldbank.org/api/v2/procnotices?format=json
    """

    def __init__(
        self,
        *,
        api_base: str = WORLDBANK_PROC_NOTICES_API,
        user_agent: str = "JobHunter/0.1 (+worldbank-procurement-connector)",
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_base = api_base
        self._user_agent = user_agent
        self._timeout = timeout_seconds

    def search_notices(
        self,
        *,
        keyword: str | None = None,
        offset: int = 0,
        rows: int = 25,
    ) -> WorldBankSearchPage:
        if rows < 1:
            return WorldBankSearchPage(notices=[], offset=offset, rows=rows, total=0)
        params: dict[str, str] = {
            "format": "json",
            "os": str(max(0, offset)),
            "rows": str(rows),
        }
        if keyword and keyword.strip():
            params["qterm"] = keyword.strip()
        url = f"{self._api_base}?{urllib.parse.urlencode(params)}"
        body = self._get_json(url)
        notices_raw = body.get("procnotices")
        if isinstance(notices_raw, list):
            notices = list(notices_raw)
        elif isinstance(notices_raw, dict):
            single = notices_raw.get("procnotice")
            if isinstance(single, list):
                notices = list(single)
            elif isinstance(single, dict):
                notices = [single]
            else:
                notices = []
        else:
            notices = []
        total = int(body.get("total") or 0)
        return WorldBankSearchPage(
            notices=notices,
            offset=int(body.get("os") or offset),
            rows=int(body.get("rows") or rows),
            total=total,
        )

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
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"World Bank procnotices request failed ({exc.code}): {detail}"
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError("World Bank procnotices response must be a JSON object")
        return payload
