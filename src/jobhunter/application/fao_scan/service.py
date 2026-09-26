"""Orchestrate FAO acquisition, SourceScan, and Phase 5 processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.connectors.fao.connector import FaoJobsConnector
from jobhunter.connectors.fao.identity import (
    FAO_JOBS_ENTRY_URL,
    FAO_JOBS_NAME,
    FAO_JOBS_ORGANISATION,
    FAO_JOBS_SOURCE_ID,
)
from jobhunter.connectors.fao.normalizer import FaoOpportunityNormalizer
from jobhunter.domain import JobSource
from jobhunter.domain.source_scan import SourceScan
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from jobhunter.infrastructure.persistence.source_scan_repository import (
    SourceScanRepository,
)


@dataclass(slots=True)
class FaoScanReport:
    scan: SourceScan
    retrieved: int = 0
    processed: int = 0
    failed: int = 0
    created_opportunities: int = 0
    processing_errors: list[str] = field(default_factory=list)
    mapping_errors: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        return [
            f"SourceScan {self.scan.id} status={self.scan.status.value}",
            f"Retrieved: {self.retrieved}",
            f"Processed: {self.processed}",
            f"Failed: {self.failed}",
            f"New canonical opportunities: {self.created_opportunities}",
        ]


class FaoScanService:
    def __init__(
        self,
        session: Session,
        connector: FaoJobsConnector | None = None,
    ) -> None:
        self._session = session
        self._connector = connector or FaoJobsConnector()
        self._sources = JobSourceRepository(session)
        self._scans = SourceScanRepository(session)
        self._processor = OpportunityProcessingService(
            session, FaoOpportunityNormalizer()
        )
        self._eligibility = EligibilityFilterService(session)

    def ensure_job_source(self) -> JobSource:
        existing = self._sources.get_by_id(FAO_JOBS_SOURCE_ID)
        if existing is not None:
            return existing
        return self._sources.save(
            JobSource(
                id=FAO_JOBS_SOURCE_ID,
                name=FAO_JOBS_NAME,
                organisation=FAO_JOBS_ORGANISATION,
                url=FAO_JOBS_ENTRY_URL,
                is_active=True,
            )
        )

    def run_scan(
        self,
        *,
        keyword: str | None = None,
        limit: int = 10,
        apply: bool = True,
    ) -> FaoScanReport:
        started = datetime.now(timezone.utc)
        if apply:
            source = self.ensure_job_source()
        else:
            source = JobSource(
                id=FAO_JOBS_SOURCE_ID,
                name=FAO_JOBS_NAME,
                organisation=FAO_JOBS_ORGANISATION,
                url=FAO_JOBS_ENTRY_URL,
            )
        scan = SourceScan(source_id=source.id, started_at=started)
        if apply:
            scan = self._scans.save(scan)

        fetch = self._connector.fetch_requisitions(keyword=keyword, limit=limit)
        retrieved = len(fetch.records)
        mapping = self._connector.map_to_raw_opportunities(
            fetch.records,
            source_id=source.id,
            scan_id=scan.id,
            retrieved_at=started,
        )

        processed = 0
        failed = len(mapping.errors)
        created = 0
        processing_errors: list[str] = list(mapping.errors)

        if apply:
            for raw in mapping.raw_opportunities:
                try:
                    result = self._processor.process(raw)
                    self._eligibility.evaluate_and_persist(result.opportunity.id)
                    processed += 1
                    if result.created_opportunity:
                        created += 1
                except Exception as exc:  # noqa: BLE001 — scan continues
                    failed += 1
                    processing_errors.append(
                        f"{raw.source_reference or raw.id}: {exc}"
                    )

        completed = datetime.now(timezone.utc)
        status = self._resolve_status(
            retrieved=retrieved,
            processed=processed if apply else 0,
            failed=failed,
            apply=apply,
        )
        error_summary = self._build_error_summary(processing_errors)

        scan.completed_at = completed
        scan.status = status
        scan.records_retrieved = retrieved
        scan.records_processed = processed if apply else 0
        scan.records_failed = failed
        scan.error_summary = error_summary
        if apply:
            scan = self._scans.save(scan)

        return FaoScanReport(
            scan=scan,
            retrieved=retrieved,
            processed=processed if apply else 0,
            failed=failed,
            created_opportunities=created,
            processing_errors=processing_errors,
            mapping_errors=mapping.errors,
        )

    @staticmethod
    def _resolve_status(
        *,
        retrieved: int,
        processed: int,
        failed: int,
        apply: bool,
    ) -> SourceScanStatus:
        if not apply:
            return SourceScanStatus.SUCCESS
        if retrieved == 0 and failed == 0:
            return SourceScanStatus.SUCCESS
        if failed == 0 and processed > 0:
            return SourceScanStatus.SUCCESS
        if processed > 0 and failed > 0:
            return SourceScanStatus.PARTIAL
        if failed > 0 and processed == 0:
            return SourceScanStatus.FAILED
        return SourceScanStatus.SUCCESS

    @staticmethod
    def _build_error_summary(errors: list[str]) -> str | None:
        if not errors:
            return None
        head = errors[:5]
        summary = "; ".join(head)
        if len(errors) > 5:
            summary += f"; … and {len(errors) - 5} more"
        return summary[:4000]
