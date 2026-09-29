"""UNDP Jobs acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.undp.client import UndpJobsClient
from jobhunter.connectors.undp.mapper import map_undp_item_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class UndpScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class UndpJobsConnector:
    """Retrieve UNDP vacancies from the official RSS feed."""

    def __init__(self, client: UndpJobsClient | None = None) -> None:
        self._client = client or UndpJobsClient()

    def fetch_vacancies(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
    ) -> UndpScanResult:
        if limit <= 0:
            return UndpScanResult()

        page = self._client.fetch_feed()
        items = list(page.items)
        if keyword and keyword.strip():
            needle = keyword.strip().lower()
            items = [
                item
                for item in items
                if needle in str(item.get("title") or "").lower()
            ]
        return UndpScanResult(records=items[:limit])

    def map_to_raw_opportunities(
        self,
        records: list[dict[str, Any]],
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> UndpScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = []
        for record in records:
            link = record.get("link", "?")
            try:
                raw_list.append(
                    map_undp_item_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                    )
                )
            except ValueError as exc:
                errors.append(f"item {link}: {exc}")
        return UndpScanResult(
            records=records, raw_opportunities=raw_list, errors=errors
        )
