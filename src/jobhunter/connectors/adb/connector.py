"""ADB CSRN acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.adb.client import AdbCsrnClient
from jobhunter.connectors.adb.mapper import map_adb_notice_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class AdbCsrnScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pages_fetched: int = 0


class AdbCsrnConnector:
    def __init__(self, client: AdbCsrnClient | None = None) -> None:
        self._client = client or AdbCsrnClient()

    def fetch_notices(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
        fetch_details: bool = False,
    ) -> AdbCsrnScanResult:
        if limit <= 0:
            return AdbCsrnScanResult()

        errors: list[str] = []
        if fetch_details:
            errors.append(
                "ADB CSRN detail pages require Oracle popup navigation; "
                "fetch_details is ignored (listing fields only)."
            )

        listing = self._client.fetch_notices(keyword=keyword, limit=limit)
        if listing.parse_error:
            errors.append(listing.parse_error)

        return AdbCsrnScanResult(
            records=listing.notices,
            errors=errors,
            pages_fetched=listing.pages_fetched,
        )

    def map_to_raw_opportunities(
        self,
        fetch_result: AdbCsrnScanResult,
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> AdbCsrnScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = list(fetch_result.errors)
        for record in fetch_result.records:
            notice_id = record.get("notice_id")
            try:
                raw_list.append(
                    map_adb_notice_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                    )
                )
            except ValueError as exc:
                errors.append(f"notice {notice_id}: {exc}")
        return AdbCsrnScanResult(
            records=fetch_result.records,
            raw_opportunities=raw_list,
            errors=errors,
            pages_fetched=fetch_result.pages_fetched,
        )
