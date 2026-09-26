"""PostgreSQL integration tests for project spreadsheet import."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.infrastructure.importers.project_spreadsheet import (
    ProjectSpreadsheetImporter,
)
from jobhunter.infrastructure.persistence.profile_models import (
    AssignmentCapabilityRow,
    AssignmentRow,
    CapabilityRow,
    ProfileDocumentRow,
)
from importers.synthetic_workbook import (
    DATA_START_ROW,
    SYNTH_SEQUENCE_ALPHA,
    write_synthetic_workbook,
)

pytestmark = pytest.mark.integration


def _counts(session: Session) -> tuple[int, int, int, int]:
    docs = session.scalar(select(func.count()).select_from(ProfileDocumentRow)) or 0
    caps = session.scalar(select(func.count()).select_from(CapabilityRow)) or 0
    asgs = session.scalar(select(func.count()).select_from(AssignmentRow)) or 0
    links = (
        session.scalar(select(func.count()).select_from(AssignmentCapabilityRow)) or 0
    )
    return docs, caps, asgs, links


def test_dry_run_writes_nothing(db_session: Session, tmp_path: Path) -> None:
    path = tmp_path / "synthetic.xlsx"
    write_synthetic_workbook(path)
    before = _counts(db_session)
    importer = ProjectSpreadsheetImporter(db_session)
    report = importer.run(path, apply=False)
    assert not report.has_errors()
    after = _counts(db_session)
    assert before == after
    assert report.capabilities_created > 0
    assert report.assignment_capabilities_created > 0


def test_apply_and_rerun_is_idempotent(db_session: Session, tmp_path: Path) -> None:
    path = tmp_path / "synthetic.xlsx"
    write_synthetic_workbook(path)
    importer = ProjectSpreadsheetImporter(db_session)

    first = importer.run(path, apply=True)
    assert not first.has_errors()
    assert first.applied

    second = importer.run(path, apply=False)
    assert not second.has_errors()
    assert second.capabilities_created == 0
    assert second.assignments_created == 0
    assert second.assignment_capabilities_created == 0
    assert second.assignment_capabilities_deleted == 0
    assert second.capabilities_unchanged == 3


def test_apply_updates_assignment_and_syncs_removed_capability_link(
    db_session: Session, tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic.xlsx"
    write_synthetic_workbook(path)
    importer = ProjectSpreadsheetImporter(db_session)
    importer.run(path, apply=True)

    import openpyxl

    wb = openpyxl.load_workbook(path)
    project = wb["Project"]
    project.cell(row=DATA_START_ROW, column=3, value="Project Alpha Updated")
    wb.save(path)
    wb.close()

    report = importer.run(path, apply=True)
    assert not report.has_errors()
    assert report.assignments_updated >= 1

    from jobhunter.infrastructure.persistence.profile_repositories import (
        AssignmentRepository,
    )

    repo = AssignmentRepository(db_session)
    from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
        assignment_id,
    )

    assignment = repo.get_by_id(
        assignment_id(path.as_posix(), SYNTH_SEQUENCE_ALPHA)
    )
    assert assignment is not None
    assert assignment.project_name == "Project Alpha Updated"

