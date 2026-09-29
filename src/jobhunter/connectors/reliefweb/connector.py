"""ReliefWeb Jobs acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.reliefweb.client import ReliefWebJobsClient
from jobhunter.connectors.reliefweb.mapper import map_reliefweb_job_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class ReliefWebScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ReliefWebJobsConnector:
    def __init__(self, client: ReliefWebJobsClient) -> None:
        self._client = client

    def fetch_jobs(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
    ) -> ReliefWebScanResult:
        if limit <= 0:
            return ReliefWebScanResult()
        page = self._client.search_jobs(keyword=keyword, limit=limit)
        return ReliefWebScanResult(records=page.jobs[:limit])

    def map_to_raw_opportunities(
        self,
        fetch_result: ReliefWebScanResult,
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> ReliefWebScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = []
        for record in fetch_result.records:
            job_id = record.get("id")
            try:
                raw_list.append(
                    map_reliefweb_job_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                    )
                )
            except ValueError as exc:
                errors.append(f"job {job_id}: {exc}")
        return ReliefWebScanResult(
            records=fetch_result.records,
            raw_opportunities=raw_list,
            errors=errors,
        )
