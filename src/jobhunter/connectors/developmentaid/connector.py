"""DevelopmentAid Jobs acquisition connector."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jobhunter.connectors.developmentaid.client import (
    DevelopmentAidJobsClient,
    DevelopmentAidRateLimitExhausted,
)
from jobhunter.connectors.developmentaid.http_policy import DevelopmentAidHttpPolicy
from jobhunter.connectors.developmentaid.mapper import (
    map_developmentaid_job_to_raw_for_scan,
)
from jobhunter.domain.raw_opportunity import RawOpportunity

logger = logging.getLogger(__name__)

SleepFn = Callable[[float], None]


@dataclass(slots=True)
class DevelopmentAidScanResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_opportunities: list[RawOpportunity] = field(default_factory=list)
    detail_errors: list[str] = field(default_factory=list)
    mapping_errors: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        return list(self.detail_errors) + list(self.mapping_errors)


class DevelopmentAidJobsConnector:
    """Retrieve DevelopmentAid vacancies and map them to RawOpportunity."""

    def __init__(
        self,
        client: DevelopmentAidJobsClient | None = None,
        *,
        policy: DevelopmentAidHttpPolicy | None = None,
        sleep: SleepFn | None = None,
    ) -> None:
        policy = policy or DevelopmentAidHttpPolicy()
        if client is None:
            client = DevelopmentAidJobsClient(policy=policy, sleep=sleep)
        self._client = client
        self._policy = policy
        self._sleep = sleep if sleep is not None else _default_sleep

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

        records = collected[:limit]
        details: dict[str, dict[str, Any]] = {}
        detail_errors: list[str] = []

        if fetch_details and records:
            logger.info(
                "DevelopmentAid: %s list record(s) retrieved; fetching details sequentially",
                len(records),
            )
            consecutive_rate_limit_stops = 0
            stopped_early = False

            for index, item in enumerate(records, start=1):
                if stopped_early:
                    break
                job_id = item.get("id")
                if job_id is None:
                    continue
                if index > 1:
                    self._sleep(self._policy.detail_interval_seconds)
                try:
                    details[str(job_id)] = self._client.get_job(job_id)
                    consecutive_rate_limit_stops = 0
                except DevelopmentAidRateLimitExhausted as exc:
                    consecutive_rate_limit_stops += 1
                    detail_errors.append(
                        f"job {job_id} detail: HTTP 429 Too Many Attempts "
                        f"({exc.attempts} attempt(s))"
                    )
                    logger.warning(
                        "DevelopmentAid: detail %s/%s rate-limited after retries",
                        index,
                        len(records),
                    )
                    if (
                        consecutive_rate_limit_stops
                        >= self._policy.consecutive_rate_limit_stop
                    ):
                        remaining = len(records) - index
                        stopped_early = True
                        detail_errors.append(
                            "DevelopmentAid: detail acquisition paused after "
                            f"sustained rate limiting; {remaining} remaining "
                            "detail fetch(es) skipped (list data retained)."
                        )
                        logger.warning(
                            "DevelopmentAid: stopping detail fetches after %s "
                            "consecutive rate-limit exhaustion(s); %s skipped",
                            consecutive_rate_limit_stops,
                            remaining,
                        )
                except RuntimeError as exc:
                    consecutive_rate_limit_stops = 0
                    detail_errors.append(f"job {job_id} detail: {exc}")

            logger.info(
                "DevelopmentAid: %s opportunities in list; %s detail(s) fetched; "
                "%s detail error(s)",
                len(records),
                len(details),
                len(detail_errors),
            )

        return DevelopmentAidScanResult(
            records=records,
            details=details,
            detail_errors=detail_errors,
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
        mapping_errors: list[str] = []
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
                mapping_errors.append(f"job {job_id}: {exc}")
        return DevelopmentAidScanResult(
            records=fetch_result.records,
            details=fetch_result.details,
            raw_opportunities=raw_list,
            detail_errors=list(fetch_result.detail_errors),
            mapping_errors=mapping_errors,
        )


def _default_sleep(seconds: float) -> None:
    import time

    time.sleep(seconds)
