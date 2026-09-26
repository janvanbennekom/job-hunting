"""Integration test for assignment-capability synchronization."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from jobhunter.infrastructure.importers.project_spreadsheet import (
    ProjectSpreadsheetImporter,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentCapabilityRepository,
)
from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    assignment_id,
)
from importers.synthetic_workbook import (
    DATA_START_ROW,
    SYNTH_CODE_API,
    SYNTH_SEQUENCE_ALPHA,
    write_synthetic_workbook,
)

pytestmark = pytest.mark.integration


def test_removed_capability_link_is_synchronized_on_apply(
    db_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "synthetic.xlsx"
    write_synthetic_workbook(path)
    importer = ProjectSpreadsheetImporter(db_session)
    importer.run(path, apply=True)

    import openpyxl

    wb = openpyxl.load_workbook(path)
    project = wb["Project"]
    project.cell(row=DATA_START_ROW, column=17, value="")
    wb.save(path)
    wb.close()

    preview = importer.run(path, apply=False)
    assert not preview.has_errors()
    assert preview.assignment_capabilities_deleted >= 1

    importer.run(path, apply=True)
    links = AssignmentCapabilityRepository(db_session).list_for_assignment(
        assignment_id(path.as_posix(), SYNTH_SEQUENCE_ALPHA)
    )
    codes = {link.capability_id for link in links}
    from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
        capability_id,
    )

    assert capability_id(SYNTH_CODE_API) not in codes
