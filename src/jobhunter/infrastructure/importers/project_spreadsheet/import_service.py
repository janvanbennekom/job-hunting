"""Apply or dry-run project spreadsheet import."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from jobhunter.domain import (
    Assignment,
    AssignmentCapability,
    Capability,
    ProfileDocument,
    ProfileDocumentType,
)
from jobhunter.infrastructure.importers.project_spreadsheet.categories import (
    GROUP_TO_CATEGORY,
)
from jobhunter.infrastructure.importers.project_spreadsheet.identity import (
    assignment_capability_id,
    assignment_id,
    capability_id,
    profile_document_id,
)
from jobhunter.infrastructure.importers.project_spreadsheet.reader import read_workbook
from jobhunter.infrastructure.importers.project_spreadsheet.report import ImportReport
from jobhunter.infrastructure.importers.project_spreadsheet.types import (
    CapabilityDefinitionRow,
    ProjectRow,
    WorkbookSnapshot,
)
from jobhunter.infrastructure.importers.project_spreadsheet.validation import (
    validate_snapshot,
)
from jobhunter.infrastructure.persistence.profile_models import AssignmentCapabilityRow
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentCapabilityRepository,
    AssignmentRepository,
    CapabilityRepository,
    ProfileDocumentRepository,
)

class ProjectSpreadsheetImporter:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._documents = ProfileDocumentRepository(session)
        self._capabilities = CapabilityRepository(session)
        self._assignments = AssignmentRepository(session)
        self._links = AssignmentCapabilityRepository(session)

    def run(self, source: Path, *, apply: bool = False) -> ImportReport:
        snapshot = read_workbook(source)
        report = ImportReport(
            source_path=snapshot.source_path,
            source_reference=snapshot.source_reference,
            dry_run=not apply,
            project_rows_read=len(snapshot.project_rows),
            experience_types_rows_read=len(snapshot.capability_definitions),
            capability_definitions_accepted=len(snapshot.capability_definitions),
        )

        errors, warnings = validate_snapshot(snapshot, source)
        report.errors.extend(errors)
        report.warnings.extend(warnings)
        if report.has_errors():
            return report

        doc_entity = self._build_profile_document(snapshot)
        report.profile_document_id = doc_entity.id

        capability_entities = {
            d.code: self._build_capability(d, doc_entity.id)
            for d in snapshot.capability_definitions
        }
        assignment_entities = {
            row.sequence: self._build_assignment(row, doc_entity.id, snapshot.source_reference)
            for row in snapshot.project_rows
            if row.sequence is not None
        }
        desired_links: dict[tuple[str, str], AssignmentCapability] = {}
        for row in snapshot.project_rows:
            if row.sequence is None:
                continue
            aid = assignment_entities[row.sequence].id
            for code in row.capability_codes:
                cap = capability_entities[code]
                desired_links[(aid, cap.id)] = AssignmentCapability(
                    id=assignment_capability_id(aid, cap.id),
                    assignment_id=aid,
                    capability_id=cap.id,
                    source_document_id=doc_entity.id,
                )

        self._diff_profile_document(doc_entity, report)
        for code, entity in capability_entities.items():
            self._diff_capability(entity, report)
        for row in snapshot.project_rows:
            if row.sequence is None:
                continue
            self._diff_assignment(assignment_entities[row.sequence], report)
        self._diff_links(doc_entity.id, desired_links, report)

        if apply:
            self._persist(
                doc_entity,
                capability_entities,
                assignment_entities,
                desired_links,
                report,
            )
            report.applied = True

        return report

    def _build_profile_document(self, snapshot: WorkbookSnapshot) -> ProfileDocument:
        return ProfileDocument(
            id=profile_document_id(snapshot.source_reference),
            document_type=ProfileDocumentType.PROJECT_DATA,
            title="Professional project spreadsheet",
            source_reference=snapshot.source_reference,
            version_label=Path(snapshot.source_path).name,
        )

    def _build_capability(
        self, row: CapabilityDefinitionRow, source_document_id: str
    ) -> Capability:
        category = GROUP_TO_CATEGORY[row.group]
        return Capability(
            id=capability_id(row.code),
            code=row.code,
            name=row.topic,
            category=category,
            description=row.description,
            is_active=True,
            source_document_id=source_document_id,
        )

    def _build_assignment(
        self, row: ProjectRow, source_document_id: str, source_reference: str
    ) -> Assignment:
        assert row.sequence is not None
        return Assignment(
            id=assignment_id(source_reference, row.sequence),
            source_record_id=row.source_record_id,
            sequence=row.sequence,
            project_name=row.project_name,
            role=row.role,
            beneficiary=row.beneficiary,
            donor=row.donor,
            country=row.country,
            period_text=row.period_text,
            working_days=row.working_days,
            last_active_year=row.last_active_year,
            description=row.description,
            responsibilities=row.responsibilities,
            tools_technologies_text=row.tools_technologies_text,
            web_link=row.web_link,
            source_document_id=source_document_id,
        )

    def _diff_profile_document(self, entity: ProfileDocument, report: ImportReport) -> None:
        existing = self._documents.get_by_id(entity.id)
        if existing is None:
            report.profile_documents_created = 1
            return
        if existing == entity:
            report.profile_documents_unchanged = 1
        else:
            report.profile_documents_updated = 1

    def _diff_capability(self, entity: Capability, report: ImportReport) -> None:
        existing = self._capabilities.get_by_id(entity.id)
        if existing is None:
            report.capabilities_created += 1
            return
        if existing == entity:
            report.capabilities_unchanged += 1
        else:
            report.capabilities_updated += 1

    def _diff_assignment(self, entity: Assignment, report: ImportReport) -> None:
        existing = self._assignments.get_by_id(entity.id)
        if existing is None:
            report.assignments_created += 1
            return
        if existing == entity:
            report.assignments_unchanged += 1
        else:
            report.assignments_updated += 1

    def _diff_links(
        self,
        source_document_id: str,
        desired: dict[tuple[str, str], AssignmentCapability],
        report: ImportReport,
    ) -> None:
        existing_pairs: set[tuple[str, str]] = set()
        for assignment in self._assignments.list_by_source_document_id(source_document_id):
            for link in self._links.list_for_assignment(assignment.id):
                if link.source_document_id == source_document_id:
                    existing_pairs.add((link.assignment_id, link.capability_id))

        desired_pairs = set(desired.keys())
        report.assignment_capabilities_created = len(desired_pairs - existing_pairs)
        report.assignment_capabilities_deleted = len(existing_pairs - desired_pairs)
        report.assignment_capabilities_unchanged = len(desired_pairs & existing_pairs)

    def _persist(
        self,
        document: ProfileDocument,
        capabilities: dict[str, Capability],
        assignments: dict[str, Assignment],
        desired_links: dict[tuple[str, str], AssignmentCapability],
        report: ImportReport,
    ) -> None:
        self._documents.save(document)
        for capability in capabilities.values():
            self._capabilities.save(capability)
        for assignment in assignments.values():
            self._assignments.save(assignment)

        source_document_id = document.id
        assignment_ids = [a.id for a in assignments.values()]
        if assignment_ids:
            stmt = delete(AssignmentCapabilityRow).where(
                AssignmentCapabilityRow.assignment_id.in_(assignment_ids),
                AssignmentCapabilityRow.source_document_id == source_document_id,
            )
            self._session.execute(stmt)

        for link in desired_links.values():
            self._links.save(link)

        self._session.flush()
