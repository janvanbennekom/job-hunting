"""CV profile seed run report."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CvSeedReport:
    seed_path: str
    source_reference: str
    profile_document_id: str | None = None
    dry_run: bool = True
    applied: bool = False

    skills_in_seed: int = 0
    languages_in_seed: int = 0
    countries_in_seed: int = 0

    profile_documents_created: int = 0
    profile_documents_updated: int = 0
    profile_documents_unchanged: int = 0

    professional_profiles_created: int = 0
    professional_profiles_updated: int = 0
    professional_profiles_unchanged: int = 0

    skills_created: int = 0
    skills_updated: int = 0
    skills_unchanged: int = 0
    skills_deleted: int = 0

    languages_created: int = 0
    languages_updated: int = 0
    languages_unchanged: int = 0
    languages_deleted: int = 0

    countries_created: int = 0
    countries_updated: int = 0
    countries_unchanged: int = 0
    countries_deleted: int = 0

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
            f"  Skills in seed: {self.skills_in_seed}",
            f"  Languages in seed: {self.languages_in_seed}",
            f"  Countries in seed: {self.countries_in_seed}",
            "",
            "Changes:",
            f"  ProfileDocuments: +{self.profile_documents_created} "
            f"~{self.profile_documents_updated} ={self.profile_documents_unchanged}",
            f"  ProfessionalProfiles: +{self.professional_profiles_created} "
            f"~{self.professional_profiles_updated} "
            f"={self.professional_profiles_unchanged}",
            f"  Skills: +{self.skills_created} ~{self.skills_updated} "
            f"={self.skills_unchanged} -{self.skills_deleted}",
            f"  Languages: +{self.languages_created} ~{self.languages_updated} "
            f"={self.languages_unchanged} -{self.languages_deleted}",
            f"  Countries: +{self.countries_created} ~{self.countries_updated} "
            f"={self.countries_unchanged} -{self.countries_deleted}",
        ]
        if self.errors:
            lines.extend(["", f"Errors ({len(self.errors)}):"])
            lines.extend(f"  - {e}" for e in self.errors)
        return lines
