"""FAO Jobs acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.fao.client import FaoJobsClient
from jobhunter.connectors.fao.mapper import map_fao_requisition_to_raw_for_scan
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class FaoScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class FaoJobsConnector:
    """Retrieve FAO vacancies and map them to RawOpportunity."""

    def __init__(self, client: FaoJobsClient | None = None) -> None:
        self._client = client or FaoJobsClient()

    def fetch_requisitions(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
    ) -> FaoScanResult:
        if limit <= 0:
            return FaoScanResult()

        self._client.ensure_session()
        collected: list[dict[str, Any]] = []
        page = 1
        while len(collected) < limit:
            page_result = self._client.search_jobs(keyword=keyword, page_no=page)
            if not page_result.requisition_list:
                break
            for item in page_result.requisition_list:
                collected.append(item)
                if len(collected) >= limit:
                    break
            if page_result.current_page * page_result.page_size >= page_result.total_count:
                break
            page += 1

        return FaoScanResult(records=collected[:limit])

    def map_to_raw_opportunities(
        self,
        records: list[dict[str, Any]],
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> FaoScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = []
        for record in records:
            try:
                raw_list.append(
                    map_fao_requisition_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                    )
                )
            except ValueError as exc:
                job_id = record.get("jobId", "?")
                errors.append(f"job {job_id}: {exc}")
        return FaoScanResult(
            records=records, raw_opportunities=raw_list, errors=errors
        )
