"""Registry of source-neutral scan adapters for automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from jobhunter.application.developmentaid_scan import DevelopmentAidScanService
from jobhunter.application.fao_scan import FaoScanService
from jobhunter.application.afdb_scan import AfdbScanService
from jobhunter.application.undp_scan import UndpScanService
from jobhunter.application.reliefweb_scan import ReliefWebScanService
from jobhunter.application.ted_scan import TedScanService
from jobhunter.application.worldbank_scan import WorldBankScanService
from jobhunter.domain.source_scan_enums import SourceScanStatus
from jobhunter.infrastructure.automation.config import SourceAutomationConfig


@dataclass(slots=True)
class SourceAdapterResult:
    source_key: str
    source_id: str
    source_scan_id: str | None
    scan_status: SourceScanStatus | None
    retrieved: int = 0
    processed: int = 0
    failed: int = 0
    created_opportunities: int = 0
    processed_opportunity_ids: list[str] = field(default_factory=list)
    new_opportunity_ids: list[str] = field(default_factory=list)
    materially_updated_opportunity_ids: list[str] = field(
        default_factory=list
    )
    error_message: str | None = None
    processing_errors: list[str] = field(default_factory=list)


class SourceScanAdapter(Protocol):
    key: str

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult: ...


class FaoSourceScanAdapter:
    key = "fao"

    def __init__(self, scan_service_factory=FaoScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


class AfdbSourceScanAdapter:
    key = "afdb"

    def __init__(self, scan_service_factory=AfdbScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            fetch_details=source_config.fetch_details,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


class UndpSourceScanAdapter:
    key = "undp"

    def __init__(self, scan_service_factory=UndpScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


class WorldBankSourceScanAdapter:
    key = "worldbank"

    def __init__(self, scan_service_factory=WorldBankScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


class ReliefWebSourceScanAdapter:
    key = "reliefweb"

    def __init__(self, scan_service_factory=ReliefWebScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


class TedSourceScanAdapter:
    key = "ted"

    def __init__(self, scan_service_factory=TedScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


class DevelopmentAidSourceScanAdapter:
    key = "developmentaid"

    def __init__(self, scan_service_factory=DevelopmentAidScanService) -> None:
        self._scan_service_factory = scan_service_factory

    def run(
        self,
        session: Session,
        source_config: SourceAutomationConfig,
        *,
        apply: bool,
        run_profile_assessment: bool,
    ) -> SourceAdapterResult:
        service = self._scan_service_factory(session)
        keyword = source_config.keyword or None
        report = service.run_scan(
            keyword=keyword,
            limit=source_config.limit,
            apply=apply,
            fetch_details=source_config.fetch_details,
            run_profile_assessment=run_profile_assessment,
        )
        return SourceAdapterResult(
            source_key=self.key,
            source_id=report.scan.source_id,
            source_scan_id=report.scan.id if apply else None,
            scan_status=report.scan.status,
            retrieved=report.retrieved,
            processed=report.processed,
            failed=report.failed,
            created_opportunities=report.created_opportunities,
            processed_opportunity_ids=list(report.processed_opportunity_ids),
            new_opportunity_ids=list(report.new_opportunity_ids),
            materially_updated_opportunity_ids=list(
                report.materially_updated_opportunity_ids
            ),
            processing_errors=list(report.processing_errors),
        )


def default_source_adapters() -> dict[str, SourceScanAdapter]:
    adapters: list[SourceScanAdapter] = [
        FaoSourceScanAdapter(),
        DevelopmentAidSourceScanAdapter(),
        WorldBankSourceScanAdapter(),
        UndpSourceScanAdapter(),
        AfdbSourceScanAdapter(),
        ReliefWebSourceScanAdapter(),
        TedSourceScanAdapter(),
    ]
    return {adapter.key: adapter for adapter in adapters}


def get_adapter(
    key: str, registry: dict[str, SourceScanAdapter] | None = None
) -> SourceScanAdapter:
    mapping = registry or default_source_adapters()
    adapter = mapping.get(key)
    if adapter is None:
        raise KeyError(f"No source scan adapter registered for key {key!r}")
    return adapter
