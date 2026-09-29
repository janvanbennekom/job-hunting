"""AfDB consultant opportunities acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.afdb.client import AfdbConsultantsClient
from jobhunter.connectors.afdb.detail import AfdbDetailPage
from jobhunter.connectors.afdb.mapper import extract_afdb_node_id, map_afdb_item_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class AfdbScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, AfdbDetailPage] = field(default_factory=dict)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class AfdbConsultantsConnector:
    def __init__(self, client: AfdbConsultantsClient | None = None) -> None:
        self._client = client or AfdbConsultantsClient()

    def fetch_opportunities(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
        fetch_details: bool = True,
    ) -> AfdbScanResult:
        if limit <= 0:
            return AfdbScanResult()

        page = self._client.fetch_feed()
        items = list(page.items)
        if keyword and keyword.strip():
            needle = keyword.strip().lower()
            items = [
                item
                for item in items
                if needle in str(item.get("title") or "").lower()
            ]
        records = items[:limit]

        details: dict[str, AfdbDetailPage] = {}
        detail_errors: list[str] = []
        if fetch_details:
            for item in records:
                node_id = extract_afdb_node_id(item)
                link = item.get("link")
                if not node_id or not isinstance(link, str) or not link.strip():
                    continue
                try:
                    details[node_id] = self._client.fetch_detail(link.strip())
                except RuntimeError as exc:
                    detail_errors.append(f"node {node_id} detail: {exc}")

        return AfdbScanResult(records=records, details=details, errors=detail_errors)

    def map_to_raw_opportunities(
        self,
        fetch_result: AfdbScanResult,
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> AfdbScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = list(fetch_result.errors)
        for record in fetch_result.records:
            node_id = extract_afdb_node_id(record)
            detail = (
                fetch_result.details.get(node_id) if node_id is not None else None
            )
            try:
                raw_list.append(
                    map_afdb_item_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                        detail=detail,
                    )
                )
            except ValueError as exc:
                errors.append(f"node {node_id}: {exc}")
        return AfdbScanResult(
            records=fetch_result.records,
            details=fetch_result.details,
            raw_opportunities=raw_list,
            errors=errors,
        )
