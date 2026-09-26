"""Parsed workbook structures (not domain entities)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CapabilityDefinitionRow:
    code: str
    group: str
    topic: str
    description: str | None
    example: str | None


@dataclass(slots=True)
class CapabilityColumn:
    column_index: int
    header: str
    capability_code: str


@dataclass(slots=True)
class ProjectRow:
    excel_row_number: int
    source_record_id: str
    sequence: int | None
    project_name: str
    role: str | None
    beneficiary: str | None
    donor: str | None
    country: str | None
    period_text: str | None
    working_days: int | None
    last_active_year: int | None
    description: str | None
    responsibilities: str | None
    tools_technologies_text: str | None
    web_link: str | None
    capability_codes: frozenset[str] = field(default_factory=frozenset)


@dataclass(slots=True)
class WorkbookSnapshot:
    source_path: str
    source_reference: str
    capability_definitions: list[CapabilityDefinitionRow]
    capability_columns: list[CapabilityColumn]
    project_rows: list[ProjectRow]
