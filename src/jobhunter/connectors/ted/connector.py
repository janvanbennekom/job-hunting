"""TED EU procurement acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.ted.client import TedSearchClient
from jobhunter.connectors.ted.mapper import map_ted_notice_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class TedScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TedProcurementConnector:
    def __init__(self, client: TedSearchClient | None = None) -> None:
        self._client = client or TedSearchClient()

    def fetch_notices(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
    ) -> TedScanResult:
        if limit <= 0:
            return TedScanResult()
        page = self._client.search_notices(keyword=keyword, limit=limit)
        return TedScanResult(records=page.notices[:limit])

    def map_to_raw_opportunities(
        self,
        fetch_result: TedScanResult,
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> TedScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = []
        for record in fetch_result.records:
            pub = record.get("publication-number")
            try:
                raw_list.append(
                    map_ted_notice_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                    )
                )
            except ValueError as exc:
                errors.append(f"notice {pub}: {exc}")
        return TedScanResult(
            records=fetch_result.records,
            raw_opportunities=raw_list,
            errors=errors,
        )
