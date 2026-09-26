"""Apply curated Professional Services seed to PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from jobhunter.domain import (
    ProfessionalProfile,
    ProfessionalService,
    ProfileDocument,
    ProfileDocumentType,
)
from jobhunter.infrastructure.importers.professional_services.identity import (
    professional_profile_id,
    professional_service_id,
    profile_document_id,
)
from jobhunter.infrastructure.importers.professional_services.loader import load_seed
from jobhunter.infrastructure.importers.professional_services.report import SeedReport
from jobhunter.infrastructure.importers.professional_services.types import (
    ProfessionalServicesSeed,
)
from jobhunter.infrastructure.importers.professional_services.validation import (
    validate_seed,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    ProfessionalProfileRepository,
    ProfessionalServiceRepository,
    ProfileDocumentRepository,
)


class ProfessionalServicesSeeder:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._documents = ProfileDocumentRepository(session)
        self._profiles = ProfessionalProfileRepository(session)
        self._services = ProfessionalServiceRepository(session)

    def run(self, seed_path: Path, *, apply: bool = False) -> SeedReport:
        seed = load_seed(seed_path)
        report = SeedReport(
            seed_path=str(seed_path.resolve()),
            source_reference=seed.source_reference,
            dry_run=not apply,
            services_in_seed=len(seed.services),
        )

        errors = validate_seed(seed)
        report.errors.extend(errors)
        if report.has_errors():
            return report

        doc = self._build_document(seed)
        profile = self._build_profile(seed)
        services = {
            row.key: self._build_service(row, seed, doc.id)
            for row in seed.services
        }
        report.profile_document_id = doc.id

        self._diff_document(doc, report)
        self._diff_profile(profile, report)
        for entity in services.values():
            self._diff_service(entity, report)

        for existing in self._services.list_by_source_document_id(doc.id):
            if existing.id in {s.id for s in services.values()}:
                continue
            if existing.is_active:
                deactivated = ProfessionalService(
                    id=existing.id,
                    name=existing.name,
                    description=existing.description,
                    is_active=False,
                    source_document_id=existing.source_document_id,
                )
                if existing != deactivated:
                    report.professional_services_deactivated += 1
                if apply:
                    self._services.save(deactivated)

        if apply:
            self._documents.save(doc)
            self._profiles.save(profile)
            for entity in services.values():
                self._services.save(entity)
            self._session.flush()
            report.applied = True

        return report

    def _build_document(self, seed: ProfessionalServicesSeed) -> ProfileDocument:
        return ProfileDocument(
            id=profile_document_id(seed.source_reference),
            document_type=ProfileDocumentType.PROFESSIONAL_SERVICES,
            title=seed.document_title,
            source_reference=seed.source_reference,
            version_label=seed.document_version_label,
        )

    def _build_profile(self, seed: ProfessionalServicesSeed) -> ProfessionalProfile:
        return ProfessionalProfile(
            id=professional_profile_id(),
            display_name=seed.profile_display_name,
            positioning_summary=seed.profile_positioning_summary,
        )

    def _build_service(
        self, row, seed: ProfessionalServicesSeed, source_document_id: str
    ) -> ProfessionalService:
        return ProfessionalService(
            id=professional_service_id(seed.source_reference, row.key),
            name=row.name,
            description=row.description,
            is_active=row.is_active,
            source_document_id=source_document_id,
        )

    def _diff_document(self, entity: ProfileDocument, report: SeedReport) -> None:
        existing = self._documents.get_by_id(entity.id)
        if existing is None:
            report.profile_documents_created = 1
            return
        if existing == entity:
            report.profile_documents_unchanged = 1
        else:
            report.profile_documents_updated = 1

    def _diff_profile(self, entity: ProfessionalProfile, report: SeedReport) -> None:
        existing = self._profiles.get_by_id(entity.id)
        if existing is None:
            report.professional_profiles_created = 1
            return
        if existing == entity:
            report.professional_profiles_unchanged = 1
        else:
            report.professional_profiles_updated = 1

    def _diff_service(self, entity: ProfessionalService, report: SeedReport) -> None:
        existing = self._services.get_by_id(entity.id)
        if existing is None:
            report.professional_services_created += 1
            return
        if existing == entity:
            report.professional_services_unchanged += 1
        else:
            report.professional_services_updated += 1
