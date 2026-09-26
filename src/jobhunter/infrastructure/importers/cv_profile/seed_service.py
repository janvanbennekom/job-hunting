"""Apply curated CV profile seed to PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from jobhunter.domain import (
    CountryExperience,
    LanguageCapability,
    ProfessionalProfile,
    ProfileDocument,
    ProfileDocumentType,
    Skill,
)
from jobhunter.infrastructure.importers.country_experience_identity import (
    country_experience_id,
)
from jobhunter.infrastructure.importers.cv_profile.identity import (
    language_capability_id,
    profile_document_id,
    skill_id,
)
from jobhunter.infrastructure.importers.cv_profile.loader import load_seed
from jobhunter.infrastructure.importers.cv_profile.report import CvSeedReport
from jobhunter.infrastructure.importers.cv_profile.types import CvProfileSeed
from jobhunter.infrastructure.importers.cv_profile.validation import validate_seed
from jobhunter.infrastructure.importers.professional_services.identity import (
    professional_profile_id,
)
from jobhunter.infrastructure.persistence.profile_models import (
    CountryExperienceRow,
    LanguageCapabilityRow,
    SkillRow,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    CountryExperienceRepository,
    LanguageCapabilityRepository,
    ProfessionalProfileRepository,
    ProfileDocumentRepository,
    SkillRepository,
)


class CvProfileSeeder:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._documents = ProfileDocumentRepository(session)
        self._profiles = ProfessionalProfileRepository(session)
        self._skills = SkillRepository(session)
        self._languages = LanguageCapabilityRepository(session)
        self._countries = CountryExperienceRepository(session)

    def run(self, seed_path: Path, *, apply: bool = False) -> CvSeedReport:
        seed = load_seed(seed_path)
        report = CvSeedReport(
            seed_path=str(seed_path.resolve()),
            source_reference=seed.source_reference,
            dry_run=not apply,
            skills_in_seed=len(seed.skills),
            languages_in_seed=len(seed.languages),
            countries_in_seed=len(seed.countries),
        )

        errors = validate_seed(seed)
        report.errors.extend(errors)
        if report.has_errors():
            return report

        doc = self._build_document(seed)
        report.profile_document_id = doc.id

        skills = {
            row.key: self._build_skill(row, seed, doc.id) for row in seed.skills
        }
        languages = {
            row.key: self._build_language(row, seed, doc.id) for row in seed.languages
        }
        countries = {
            row.country: self._build_country(row, seed, doc.id) for row in seed.countries
        }

        profile = self._build_profile_update(doc.id, seed)

        self._diff_document(doc, report)
        self._diff_profile(profile, report)
        for entity in skills.values():
            self._diff_skill(entity, report)
        for entity in languages.values():
            self._diff_language(entity, report)
        for entity in countries.values():
            self._diff_country(entity, report)

        desired_skill_ids = {s.id for s in skills.values()}
        for existing in self._skills.list_by_source_document_id(doc.id):
            if existing.id not in desired_skill_ids:
                report.skills_deleted += 1
                if apply:
                    self._session.execute(
                        delete(SkillRow).where(SkillRow.id == existing.id)
                    )

        desired_language_ids = {lang.id for lang in languages.values()}
        for existing in self._languages.list_by_source_document_id(doc.id):
            if existing.id not in desired_language_ids:
                report.languages_deleted += 1
                if apply:
                    self._session.execute(
                        delete(LanguageCapabilityRow).where(
                            LanguageCapabilityRow.id == existing.id
                        )
                    )

        desired_country_ids = {c.id for c in countries.values()}
        for existing in self._countries.list_by_source_document_id(doc.id):
            if existing.id not in desired_country_ids:
                report.countries_deleted += 1
                if apply:
                    self._session.execute(
                        delete(CountryExperienceRow).where(
                            CountryExperienceRow.id == existing.id
                        )
                    )

        if apply:
            self._documents.save(doc)
            self._profiles.save(profile)
            for entity in skills.values():
                self._skills.save(entity)
            for entity in languages.values():
                self._languages.save(entity)
            for entity in countries.values():
                self._countries.save(entity)
            self._session.flush()
            report.applied = True

        return report

    def _build_document(self, seed: CvProfileSeed) -> ProfileDocument:
        return ProfileDocument(
            id=profile_document_id(seed.source_reference),
            document_type=ProfileDocumentType.CV,
            title=seed.document_title,
            source_reference=seed.source_reference,
            version_label=seed.document_version_label,
        )

    def _build_profile_update(
        self, cv_document_id: str, seed: CvProfileSeed
    ) -> ProfessionalProfile:
        existing = self._profiles.get_by_id(professional_profile_id())
        if existing is not None:
            return ProfessionalProfile(
                id=existing.id,
                display_name=existing.display_name,
                positioning_summary=existing.positioning_summary,
                primary_cv_document_id=cv_document_id,
            )
        display_name = seed.profile_display_name or "Jan van Bennekom-Minnema"
        return ProfessionalProfile(
            id=professional_profile_id(),
            display_name=display_name,
            positioning_summary=None,
            primary_cv_document_id=cv_document_id,
        )

    def _build_skill(
        self, row, seed: CvProfileSeed, source_document_id: str
    ) -> Skill:
        return Skill(
            id=skill_id(seed.source_reference, row.key),
            name=row.name,
            category=row.category,
            description=row.description,
            cv_emphasized=row.cv_emphasized,
            source_document_id=source_document_id,
        )

    def _build_language(
        self, row, seed: CvProfileSeed, source_document_id: str
    ) -> LanguageCapability:
        return LanguageCapability(
            id=language_capability_id(seed.source_reference, row.key),
            language=row.language,
            proficiency_text=row.proficiency_text,
            cefr_level=None,
            source_document_id=source_document_id,
        )

    def _build_country(
        self, row, seed: CvProfileSeed, source_document_id: str
    ) -> CountryExperience:
        return CountryExperience(
            id=country_experience_id(seed.source_reference, row.country),
            country=row.country,
            notes=row.notes,
            source_document_id=source_document_id,
        )

    def _diff_document(self, entity: ProfileDocument, report: CvSeedReport) -> None:
        existing = self._documents.get_by_id(entity.id)
        if existing is None:
            report.profile_documents_created = 1
            return
        if existing == entity:
            report.profile_documents_unchanged = 1
        else:
            report.profile_documents_updated = 1

    def _diff_profile(self, entity: ProfessionalProfile, report: CvSeedReport) -> None:
        existing = self._profiles.get_by_id(entity.id)
        if existing is None:
            report.professional_profiles_created = 1
            return
        if existing == entity:
            report.professional_profiles_unchanged = 1
        else:
            report.professional_profiles_updated = 1

    def _diff_skill(self, entity: Skill, report: CvSeedReport) -> None:
        existing = self._skills.get_by_id(entity.id)
        if existing is None:
            report.skills_created += 1
            return
        if existing == entity:
            report.skills_unchanged += 1
        else:
            report.skills_updated += 1

    def _diff_language(self, entity: LanguageCapability, report: CvSeedReport) -> None:
        existing = self._languages.get_by_id(entity.id)
        if existing is None:
            report.languages_created += 1
            return
        if existing == entity:
            report.languages_unchanged += 1
        else:
            report.languages_updated += 1

    def _diff_country(self, entity: CountryExperience, report: CvSeedReport) -> None:
        existing = self._countries.get_by_id(entity.id)
        if existing is None:
            report.countries_created += 1
            return
        if existing == entity:
            report.countries_unchanged += 1
        else:
            report.countries_updated += 1
