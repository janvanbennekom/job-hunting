"""Orchestrate ReliefWeb acquisition, SourceScan, and Phase 5 processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.eligibility import EligibilityFilterService
from jobhunter.application.opportunity_processing import OpportunityProcessingService
from jobhunter.application.profile_assessment import OpportunityProfileAssessmentService
from jobhunter.application.source_scan.outcomes import SourceScanOutcomeIds
from jobhunter.ai.factory import create_assessment_model
from jobhunter.connectors.reliefweb.client import ReliefWebApiError, ReliefWebJobsClient
from jobhunter.connectors.reliefweb.connector import ReliefWebJobsConnector
from jobhunter.connectors.reliefweb.identity import (
    RELIEFWEB_JOBS_ENTRY_URL,
    RELIEFWEB_JOBS_NAME,
    RELIEFWEB_JOBS_ORGANISATION,
    RELIEFWEB_JOBS_SOURCE_ID,
)
from jobhunter.connectors.reliefweb.normalizer import ReliefWebOpportunityNormalizer
from jobhunter.domain import JobSource
from jobhunter.domain.source_scan import SourceScan
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.config import Settings, get_settings
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from jobhunter.infrastructure.persistence.source_scan_repository import (
    SourceScanRepository,
)


@dataclass(slots=True)
class ReliefWebScanReport:
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


class ReliefWebScanService:
    def __init__(
        self,
        session: Session,
        connector: ReliefWebJobsConnector | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._connector = connector
        self._sources = JobSourceRepository(session)
        self._scans = SourceScanRepository(session)
        self._processor = OpportunityProcessingService(
            session, ReliefWebOpportunityNormalizer()
        )
        self._eligibility = EligibilityFilterService(session)

    def ensure_job_source(self) -> JobSource:
        existing = self._sources.get_by_id(RELIEFWEB_JOBS_SOURCE_ID)
        if existing is not None:
            return existing
        return self._sources.save(
            JobSource(
                id=RELIEFWEB_JOBS_SOURCE_ID,
                name=RELIEFWEB_JOBS_NAME,
                organisation=RELIEFWEB_JOBS_ORGANISATION,
                url=RELIEFWEB_JOBS_ENTRY_URL,
                is_active=True,
            )
        )

    def _connector_or_raise(self) -> ReliefWebJobsConnector:
        if self._connector is not None:
            return self._connector
        appname = self._settings.reliefweb_appname
        if not appname:
            raise RuntimeError(
                "JOBHUNTER_RELIEFWEB_APPNAME is not configured. Request a "
                "pre-approved appname from reliefweb.int/contact and set it in .env."
            )
        return ReliefWebJobsConnector(
            ReliefWebJobsClient(appname=appname),
        )

    def run_scan(
        self,
        *,
        keyword: str | None = None,
        limit: int = 10,
        apply: bool = True,
        run_profile_assessment: bool = True,
    ) -> ReliefWebScanReport:
        started = datetime.now(timezone.utc)
        if apply:
            source = self.ensure_job_source()
        else:
            source = JobSource(
                id=RELIEFWEB_JOBS_SOURCE_ID,
                name=RELIEFWEB_JOBS_NAME,
                organisation=RELIEFWEB_JOBS_ORGANISATION,
                url=RELIEFWEB_JOBS_ENTRY_URL,
            )
        scan = SourceScan(source_id=source.id, started_at=started)
        if apply:
            scan = self._scans.save(scan)

        try:
            connector = self._connector_or_raise()
        except RuntimeError as exc:
            completed = datetime.now(timezone.utc)
            scan.completed_at = completed
            scan.status = SourceScanStatus.FAILED
            scan.records_retrieved = 0
            scan.records_processed = 0
            scan.records_failed = 0
            scan.error_summary = str(exc)
            if apply:
                scan = self._scans.save(scan)
            return ReliefWebScanReport(scan=scan, processing_errors=[str(exc)])

        try:
            fetch = connector.fetch_jobs(keyword=keyword, limit=limit)
        except ReliefWebApiError as exc:
            completed = datetime.now(timezone.utc)
            scan.completed_at = completed
            scan.status = SourceScanStatus.FAILED
            scan.error_summary = str(exc)
            if apply:
                scan = self._scans.save(scan)
            return ReliefWebScanReport(
                scan=scan, processing_errors=[str(exc)]
            )

        retrieved = len(fetch.records)
        mapping = connector.map_to_raw_opportunities(
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

        return ReliefWebScanReport(
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
