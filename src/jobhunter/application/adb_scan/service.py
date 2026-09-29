"""Orchestrate ADB CSRN acquisition, SourceScan, and Phase 5 processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.application.profile_assessment import OpportunityProfileAssessmentService
from jobhunter.application.source_scan.outcomes import SourceScanOutcomeIds
from jobhunter.ai.factory import create_assessment_model
from jobhunter.connectors.adb.connector import AdbCsrnConnector
from jobhunter.connectors.adb.identity import (
    ADB_CSRN_ENTRY_URL,
    ADB_CSRN_NAME,
    ADB_CSRN_ORGANISATION,
    ADB_CSRN_SOURCE_ID,
)
from jobhunter.connectors.adb.normalizer import AdbCsrnOpportunityNormalizer
from jobhunter.domain import JobSource
from jobhunter.domain.source_scan import SourceScan
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.config import get_settings
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from jobhunter.infrastructure.persistence.source_scan_repository import (
    SourceScanRepository,
)


@dataclass(slots=True)
class AdbScanReport:
    scan: SourceScan
    retrieved: int = 0
    processed: int = 0
    failed: int = 0
    created_opportunities: int = 0
    processed_opportunity_ids: list[str] = field(default_factory=list)
    new_opportunity_ids: list[str] = field(default_factory=list)
    materially_updated_opportunity_ids: list[str] = field(default_factory=list)
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


class AdbScanService:
    def __init__(
        self,
        session: Session,
        connector: AdbCsrnConnector | None = None,
    ) -> None:
        self._session = session
        self._connector = connector or AdbCsrnConnector()
        self._sources = JobSourceRepository(session)
        self._scans = SourceScanRepository(session)
        self._processor = OpportunityProcessingService(
            session, AdbCsrnOpportunityNormalizer()
        )
        self._eligibility = EligibilityFilterService(session)

    def ensure_job_source(self) -> JobSource:
        existing = self._sources.get_by_id(ADB_CSRN_SOURCE_ID)
        if existing is not None:
            return existing
        return self._sources.save(
            JobSource(
                id=ADB_CSRN_SOURCE_ID,
                name=ADB_CSRN_NAME,
                organisation=ADB_CSRN_ORGANISATION,
                url=ADB_CSRN_ENTRY_URL,
                is_active=True,
            )
        )

    def run_scan(
        self,
        *,
        keyword: str | None = None,
        limit: int = 10,
        apply: bool = True,
        fetch_details: bool = False,
        run_profile_assessment: bool = True,
    ) -> AdbScanReport:
        started = datetime.now(timezone.utc)
        if apply:
            source = self.ensure_job_source()
        else:
            source = JobSource(
                id=ADB_CSRN_SOURCE_ID,
                name=ADB_CSRN_NAME,
                organisation=ADB_CSRN_ORGANISATION,
                url=ADB_CSRN_ENTRY_URL,
            )
        scan = SourceScan(source_id=source.id, started_at=started)
        if apply:
            scan = self._scans.save(scan)

        try:
            fetch = self._connector.fetch_notices(
                keyword=keyword,
                limit=limit,
                fetch_details=fetch_details,
            )
        except RuntimeError as exc:
            completed = datetime.now(timezone.utc)
            scan.completed_at = completed
            scan.status = SourceScanStatus.FAILED
            scan.error_summary = str(exc)
            if apply:
                scan = self._scans.save(scan)
            return AdbScanReport(scan=scan, processing_errors=[str(exc)])

        retrieved = len(fetch.records)
        mapping = self._connector.map_to_raw_opportunities(
            fetch,
            source_id=source.id,
            scan_id=scan.id,
            retrieved_at=started,
        )

        processed = 0
        failed = len(mapping.errors)
        created = 0
        processing_errors: list[str] = list(mapping.errors)
        outcome_ids = SourceScanOutcomeIds()

        if apply:
            for raw in mapping.raw_opportunities:
                try:
                    result = self._processor.process(raw)
                    self._eligibility.evaluate_and_persist(result.opportunity.id)
                    if run_profile_assessment:
                        self._assess_profile_if_configured(result.opportunity.id)
                    outcome_ids.record(result)
                    processed += 1
                    if result.created_opportunity:
                        created += 1
                except Exception as exc:  # noqa: BLE001
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
            acquisition_errors=mapping.errors,
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

        return AdbScanReport(
            scan=scan,
            retrieved=retrieved,
            processed=processed if apply else 0,
            failed=failed,
            created_opportunities=created,
            processed_opportunity_ids=outcome_ids.processed_opportunity_ids,
            new_opportunity_ids=outcome_ids.new_opportunity_ids,
            materially_updated_opportunity_ids=(
                outcome_ids.materially_updated_opportunity_ids
            ),
            processing_errors=processing_errors,
            mapping_errors=mapping.errors,
        )

    def _assess_profile_if_configured(self, opportunity_id: str) -> None:
        try:
            model = create_assessment_model(get_settings())
        except RuntimeError:
            return
        try:
            service = OpportunityProfileAssessmentService(self._session, model)
            service.assess_opportunity(opportunity_id)
        except Exception:  # noqa: BLE001
            return

    @staticmethod
    def _resolve_status(
        *,
        retrieved: int,
        processed: int,
        failed: int,
        apply: bool,
        acquisition_errors: list[str],
    ) -> SourceScanStatus:
        if not apply:
            return SourceScanStatus.SUCCESS
        if retrieved == 0 and failed == 0 and not acquisition_errors:
            return SourceScanStatus.SUCCESS
        if failed == 0 and processed > 0:
            if acquisition_errors:
                return SourceScanStatus.PARTIAL
            return SourceScanStatus.SUCCESS
        if processed > 0 and failed > 0:
            return SourceScanStatus.PARTIAL
        if failed > 0 and processed == 0:
            return SourceScanStatus.FAILED
        if acquisition_errors and retrieved > 0:
            return SourceScanStatus.PARTIAL
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
