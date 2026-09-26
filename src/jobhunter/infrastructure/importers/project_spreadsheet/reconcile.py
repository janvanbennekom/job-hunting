"""Remove spreadsheet-imported assignments so identity can be re-established."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    profile_document_id,
)
from jobhunter.infrastructure.persistence.profile_models import (
    AssignmentCapabilityRow,
    AssignmentRow,
    CapabilityRow,
    ProfileDocumentRow,
)


@dataclass(slots=True)
class PurgeReport:
    source_reference: str
    profile_document_id: str
    profile_documents: int
    capabilities: int
    assignments_deleted: int
    assignment_capabilities_deleted: int


def purge_spreadsheet_assignments(session: Session, source: Path) -> PurgeReport:
    """Delete assignments and links owned by the spreadsheet ProfileDocument.

    Capabilities and the ProfileDocument row are retained so a fresh import can
    upsert without duplicating vocabulary records.
    """
    source_reference = source.as_posix()
    doc_id = profile_document_id(source_reference)

    doc_count = (
        session.scalar(
            select(func.count())
            .select_from(ProfileDocumentRow)
            .where(ProfileDocumentRow.id == doc_id)
        )
        or 0
    )
    cap_count = (
        session.scalar(
            select(func.count())
            .select_from(CapabilityRow)
            .where(CapabilityRow.source_document_id == doc_id)
        )
        or 0
    )

    assignment_ids = list(
        session.scalars(
            select(AssignmentRow.id).where(AssignmentRow.source_document_id == doc_id)
        ).all()
    )

    links_deleted = 0
    if assignment_ids:
        links_deleted = (
            session.execute(
                delete(AssignmentCapabilityRow).where(
                    AssignmentCapabilityRow.assignment_id.in_(assignment_ids),
                    AssignmentCapabilityRow.source_document_id == doc_id,
                )
            ).rowcount
            or 0
        )

    assignments_deleted = (
        session.execute(
            delete(AssignmentRow).where(AssignmentRow.source_document_id == doc_id)
        ).rowcount
        or 0
    )

    session.flush()

    return PurgeReport(
        source_reference=source_reference,
        profile_document_id=doc_id,
        profile_documents=doc_count,
        capabilities=cap_count,
        assignments_deleted=assignments_deleted,
        assignment_capabilities_deleted=links_deleted,
    )
