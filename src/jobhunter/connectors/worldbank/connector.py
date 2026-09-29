"""World Bank procurement notices acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.worldbank.client import WorldBankProcNoticesClient
from jobhunter.connectors.worldbank.mapper import map_worldbank_notice_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class WorldBankScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class WorldBankProcNoticesConnector:
    """Retrieve World Bank procurement notices and map them to RawOpportunity."""

    def __init__(self, client: WorldBankProcNoticesClient | None = None) -> None:
        self._client = client or WorldBankProcNoticesClient()

    def fetch_notices(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
    ) -> WorldBankScanResult:
        if limit <= 0:
            return WorldBankScanResult()

        collected: list[dict[str, Any]] = []
        offset = 0
        page_size = min(limit, 100)
        while len(collected) < limit:
            page = self._client.search_notices(
                keyword=keyword,
                offset=offset,
                rows=page_size,
            )
            if not page.notices:
                break
            for item in page.notices:
                collected.append(item)
                if len(collected) >= limit:
                    break
            offset += len(page.notices)
            if offset >= page.total or len(page.notices) < page.rows:
                break

        return WorldBankScanResult(records=collected[:limit])

    def map_to_raw_opportunities(
        self,
        records: list[dict[str, Any]],
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> WorldBankScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = []
        for record in records:
            notice_id = record.get("id", "?")
            try:
                raw_list.append(
                    map_worldbank_notice_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                    )
                )
            except ValueError as exc:
                errors.append(f"notice {notice_id}: {exc}")
        return WorldBankScanResult(
            records=records, raw_opportunities=raw_list, errors=errors
        )
