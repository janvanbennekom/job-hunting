"""Seed run report."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SeedReport:
    seed_path: str
    source_reference: str
    profile_document_id: str | None = None
    dry_run: bool = True
    applied: bool = False

    services_in_seed: int = 0

    profile_documents_created: int = 0
    profile_documents_updated: int = 0
    profile_documents_unchanged: int = 0

    professional_profiles_created: int = 0
    professional_profiles_updated: int = 0
    professional_profiles_unchanged: int = 0

    professional_services_created: int = 0
    professional_services_updated: int = 0
    professional_services_unchanged: int = 0
    professional_services_deactivated: int = 0

    errors: list[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        return bool(self.errors)

    def summary_lines(self) -> list[str]:
        lines = [
            f"Seed: {self.seed_path}",
            f"Source reference: {self.source_reference}",
            f"ProfileDocument id: {self.profile_document_id}",
            f"Mode: {'dry-run' if self.dry_run else 'apply'}",
            "",
            "Input:",
            f"  Services in seed: {self.services_in_seed}",
            "",
            "Changes:",
            f"  ProfileDocuments: +{self.profile_documents_created} "
            f"~{self.profile_documents_updated} ={self.profile_documents_unchanged}",
            f"  ProfessionalProfiles: +{self.professional_profiles_created} "
            f"~{self.professional_profiles_updated} "
            f"={self.professional_profiles_unchanged}",
            f"  ProfessionalServices: +{self.professional_services_created} "
            f"~{self.professional_services_updated} "
            f"={self.professional_services_unchanged} "
            f"inactive:{self.professional_services_deactivated}",
        ]
        if self.errors:
            lines.extend(["", f"Errors ({len(self.errors)}):"])
            lines.extend(f"  - {e}" for e in self.errors)
        return lines
