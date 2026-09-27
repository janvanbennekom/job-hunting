"""DevelopmentAid Jobs acquisition connector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.developmentaid.client import DevelopmentAidJobsClient
from jobhunter.connectors.developmentaid.mapper import (
    map_developmentaid_job_to_raw_for_scan,
)
from jobhunter.domain.raw_opportunity import RawOpportunity


@dataclass(slots=True)
class DevelopmentAidScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DevelopmentAidJobsConnector:
    """Retrieve DevelopmentAid vacancies and map them to RawOpportunity."""

    def __init__(self, client: DevelopmentAidJobsClient | None = None) -> None:
        self._client = client or DevelopmentAidJobsClient()

    def fetch_jobs(
        self,
        *,
        keyword: str | None = None,
        limit: int = 25,
        fetch_details: bool = True,
    ) -> DevelopmentAidScanResult:
        if limit <= 0:
            return DevelopmentAidScanResult()

        collected: list[dict[str, Any]] = []
        page_number = 1
        page_size = min(limit, 25)
        total = None
        while len(collected) < limit:
            page = self._client.search_jobs(
                page_number=page_number,
                page_size=page_size,
                keyword=keyword,
            )
            if total is None:
                total = page.total
            if not page.items:
                break
            for item in page.items:
                collected.append(item)
                if len(collected) >= limit:
                    break
            if page_number * page.page_size >= (total or 0):
                break
            page_number += 1

        details: dict[str, dict[str, Any]] = {}
        detail_errors: list[str] = []
        if fetch_details:
            for item in collected[:limit]:
                job_id = item.get("id")
                if job_id is None:
                    continue
                try:
                    details[str(job_id)] = self._client.get_job(job_id)
                except RuntimeError as exc:
                    detail_errors.append(f"job {job_id} detail: {exc}")

        return DevelopmentAidScanResult(
            records=collected[:limit],
            details=details,
            errors=detail_errors,
        )

    def map_to_raw_opportunities(
        self,
        fetch_result: DevelopmentAidScanResult,
        *,
        source_id: str,
        scan_id: str,
        retrieved_at: datetime | None = None,
    ) -> DevelopmentAidScanResult:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        raw_list: list[RawOpportunity] = []
        errors: list[str] = list(fetch_result.errors)
        for record in fetch_result.records:
            job_id = record.get("id")
            detail = (
                fetch_result.details.get(str(job_id)) if job_id is not None else None
            )
            try:
                raw_list.append(
                    map_developmentaid_job_to_raw_for_scan(
                        record,
                        source_id=source_id,
                        scan_id=scan_id,
                        retrieved_at=retrieved,
                        detail=detail,
                    )
                )
            except ValueError as exc:
                errors.append(f"job {job_id}: {exc}")
        return DevelopmentAidScanResult(
            records=fetch_result.records,
            details=fetch_result.details,
            raw_opportunities=raw_list,
            errors=errors,
        )
