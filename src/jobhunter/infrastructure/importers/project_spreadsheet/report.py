"""Import run report."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ImportReport:
    source_path: str
    source_reference: str
    profile_document_id: str | None = None
    dry_run: bool = True
    applied: bool = False

    project_rows_read: int = 0
    experience_types_rows_read: int = 0
    capability_definitions_accepted: int = 0

    profile_documents_created: int = 0
    profile_documents_updated: int = 0
    profile_documents_unchanged: int = 0

    capabilities_created: int = 0
    capabilities_updated: int = 0
    capabilities_unchanged: int = 0

    assignments_created: int = 0
    assignments_updated: int = 0
    assignments_unchanged: int = 0

    assignment_capabilities_created: int = 0
    assignment_capabilities_deleted: int = 0
    assignment_capabilities_unchanged: int = 0

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_rows: list[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        return bool(self.errors)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Source: {self.source_path}",
            f"ProfileDocument id: {self.profile_document_id}",
            f"Mode: {'dry-run' if self.dry_run else 'apply'}",
            "",
            "Input:",
            f"  Project rows read: {self.project_rows_read}",
            f"  ExperienceTypes rows read: {self.experience_types_rows_read}",
            f"  Capability definitions accepted: {self.capability_definitions_accepted}",
            "",
            "Changes:",
            f"  ProfileDocuments: +{self.profile_documents_created} "
            f"~{self.profile_documents_updated} ={self.profile_documents_unchanged}",
            f"  Capabilities: +{self.capabilities_created} "
            f"~{self.capabilities_updated} ={self.capabilities_unchanged}",
            f"  Assignments: +{self.assignments_created} "
            f"~{self.assignments_updated} ={self.assignments_unchanged}",
            f"  AssignmentCapabilities: +{self.assignment_capabilities_created} "
            f"-{self.assignment_capabilities_deleted} "
            f"={self.assignment_capabilities_unchanged}",
        ]
        if self.warnings:
            lines.extend(["", f"Warnings ({len(self.warnings)}):"])
            lines.extend(f"  - {w}" for w in self.warnings)
        if self.errors:
            lines.extend(["", f"Errors ({len(self.errors)}):"])
            lines.extend(f"  - {e}" for e in self.errors)
        return lines
