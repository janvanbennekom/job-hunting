"""Operational source status (configuration from automation.json + DB scans)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.application.sources.dtos import SourceOperationalRow
from jobhunter.application.sources.registry import (
    connector_meta_for_key,
    job_source_id_for_key,
    list_registered_connectors,
)
from jobhunter.infrastructure.automation.config import load_automation_config
from jobhunter.infrastructure.persistence.models import OpportunitySourceRow
from jobhunter.infrastructure.persistence.repositories import JobSourceRepository
from jobhunter.infrastructure.persistence.source_scan_repository import (
    SourceScanRepository,
)


class SourceOperationalQueryService:
    """Registry-driven source overview; does not mutate strategy revisions."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._job_sources = JobSourceRepository(session)
        self._scans = SourceScanRepository(session)

    def list_sources(self) -> list[SourceOperationalRow]:
        automation = load_automation_config()
        config_by_key = {src.key: src for src in automation.sources}
        link_counts = self._opportunity_link_counts()

        rows: list[SourceOperationalRow] = []
        for meta in list_registered_connectors():
            cfg = config_by_key.get(meta.source_key)
            job_source_id = job_source_id_for_key(meta.source_key) or ""
            display_name = meta.default_display_name
            if job_source_id:
                job_source = self._job_sources.get_by_id(job_source_id)
                if job_source and job_source.name:
                    display_name = job_source.name

            scan = (
                self._scans.get_latest_for_source(job_source_id)
                if job_source_id
                else None
            )
            rows.append(
                SourceOperationalRow(
                    source_key=meta.source_key,
                    display_name=display_name,
                    connector_label=meta.connector_label,
                    job_source_id=job_source_id,
                    configured=cfg is not None,
                    enabled=cfg.enabled if cfg else False,
                    keyword=cfg.keyword if cfg else "",
                    limit=cfg.limit if cfg else 0,
                    fetch_details=cfg.fetch_details if cfg else True,
                    last_scan_started_at=(
                        scan.started_at.isoformat() if scan and scan.started_at else None
                    ),
                    last_scan_finished_at=(
                        scan.completed_at.isoformat()
                        if scan and scan.completed_at
                        else None
                    ),
                    last_scan_status=scan.status.value if scan else None,
                    last_error_summary=scan.error_summary if scan else None,
                    records_retrieved=scan.records_retrieved if scan else None,
                    records_failed=scan.records_failed if scan else None,
                    opportunity_link_count=link_counts.get(job_source_id, 0),
                )
            )
        return rows

    def _opportunity_link_counts(self) -> dict[str, int]:
        stmt = (
            select(
                OpportunitySourceRow.source_id,
                func.count(OpportunitySourceRow.id),
            )
            .group_by(OpportunitySourceRow.source_id)
        )
        return {
            source_id: int(count)
            for source_id, count in self._session.execute(stmt).all()
        }
