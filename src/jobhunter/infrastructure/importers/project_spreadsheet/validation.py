"""Validate workbook snapshot before import."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import openpyxl

from jobhunter.infrastructure.importers.project_spreadsheet.categories import (
    GROUP_TO_CATEGORY,
)
from jobhunter.infrastructure.importers.project_spreadsheet.reader import (
    PROJECT_SHEET,
    _interpret_capability_cell,
)
from jobhunter.infrastructure.importers.project_spreadsheet.types import WorkbookSnapshot


def validate_snapshot(snapshot: WorkbookSnapshot, workbook_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    codes = [d.code for d in snapshot.capability_definitions]
    for code, count in Counter(codes).items():
        if count > 1:
            errors.append(f"Duplicate capability code in ExperienceTypes: {code}")

    if not snapshot.capability_definitions:
        errors.append("No capability definitions found in ExperienceTypes")

    for definition in snapshot.capability_definitions:
        if definition.group not in GROUP_TO_CATEGORY:
            errors.append(
                f"Unknown capability group {definition.group!r} for code {definition.code}"
            )

    defined_codes = {d.code for d in snapshot.capability_definitions}
    column_codes = {c.capability_code for c in snapshot.capability_columns}
    for code in sorted(column_codes - defined_codes):
        errors.append(f"Project column maps to undefined capability code {code}")
    for code in sorted(defined_codes - column_codes):
        warnings.append(
            f"ExperienceTypes defines {code} but no matching Project capability column"
        )

    project_ids = [row.source_record_id for row in snapshot.project_rows]
    for project_id, count in Counter(project_ids).items():
        if count > 1:
            warnings.append(
                f"Duplicate Project.id {project_id!r} ({count} rows); "
                "identity uses Project.sequence, not Project.id"
            )

    sequences = [row.sequence for row in snapshot.project_rows]
    for row in snapshot.project_rows:
        if row.sequence is None:
            errors.append(
                f"Project row {row.excel_row_number} (id={row.source_record_id}): "
                "missing sequence"
            )
    for sequence, count in Counter(s for s in sequences if s is not None).items():
        if count > 1:
            errors.append(f"Duplicate Project.sequence {sequence} ({count} rows)")

    for row in snapshot.project_rows:
        if not row.project_name:
            errors.append(
                f"Project row {row.excel_row_number}: missing project name "
                f"(id={row.source_record_id})"
            )
        if row.working_days is not None and row.working_days < 0:
            errors.append(
                f"Project row {row.excel_row_number}: invalid working_days "
                f"{row.working_days}"
            )

    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        sheet = workbook[PROJECT_SHEET]
        rows = list(sheet.iter_rows(values_only=True))
        header = [str(c).strip() if c else "" for c in rows[0]]
        for row in snapshot.project_rows:
            data = rows[row.excel_row_number - 1]
            for col in snapshot.capability_columns:
                cell = data[col.column_index] if col.column_index < len(data) else None
                active, warn = _interpret_capability_cell(cell, col.capability_code)
                if warn:
                    warnings.append(
                        f"Project row {row.excel_row_number}, column {col.header}: {warn}"
                    )
                if active and col.capability_code not in row.capability_codes:
                    errors.append(
                        f"Inconsistent capability parsing row {row.excel_row_number} "
                        f"column {col.header}"
                    )
    finally:
        workbook.close()

    return errors, warnings
