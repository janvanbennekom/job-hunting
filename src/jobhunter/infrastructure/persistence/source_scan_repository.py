"""Persistence for source scan runs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain.source_scan import SourceScan
from jobhunter.infrastructure.persistence import mappers
from jobhunter.infrastructure.persistence.models import SourceScanRow


class SourceScanRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: SourceScan) -> SourceScan:
        row = mappers.source_scan_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.source_scan_to_domain(merged)

    def get_by_id(self, entity_id: str) -> SourceScan | None:
        row = self._session.get(SourceScanRow, entity_id)
        if row is None:
            return None
        return mappers.source_scan_to_domain(row)

    def list_for_source(
        self, source_id: str, *, limit: int = 20
    ) -> list[SourceScan]:
        stmt = (
            select(SourceScanRow)
            .where(SourceScanRow.source_id == source_id)
            .order_by(SourceScanRow.started_at.desc())
            .limit(limit)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.source_scan_to_domain(row) for row in rows]

    def get_latest_for_source(self, source_id: str) -> SourceScan | None:
        scans = self.list_for_source(source_id, limit=1)
        return scans[0] if scans else None
