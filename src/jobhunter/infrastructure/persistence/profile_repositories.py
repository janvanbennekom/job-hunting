"""Repositories for professional evidence entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from jobhunter.domain import (
    Assignment,
    AssignmentCapability,
    Capability,
    CountryExperience,
    LanguageCapability,
    ProfessionalProfile,
    ProfessionalService,
    ProfileDocument,
    Skill,
)
from jobhunter.infrastructure.persistence import profile_mappers as mappers
from jobhunter.infrastructure.persistence.profile_models import (
    AssignmentCapabilityRow,
    AssignmentRow,
    CapabilityRow,
    CountryExperienceRow,
    LanguageCapabilityRow,
    ProfessionalProfileRow,
    ProfessionalServiceRow,
    ProfileDocumentRow,
    SkillRow,
)


class ProfileDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: ProfileDocument) -> ProfileDocument:
        row = mappers.profile_document_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.profile_document_to_domain(merged)

    def get_by_id(self, entity_id: str) -> ProfileDocument | None:
        row = self._session.get(ProfileDocumentRow, entity_id)
        if row is None:
            return None
        return mappers.profile_document_to_domain(row)


class ProfessionalProfileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: ProfessionalProfile) -> ProfessionalProfile:
        row = mappers.professional_profile_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.professional_profile_to_domain(merged)

    def get_by_id(self, entity_id: str) -> ProfessionalProfile | None:
        row = self._session.get(ProfessionalProfileRow, entity_id)
        if row is None:
            return None
        return mappers.professional_profile_to_domain(row)


class ProfessionalServiceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: ProfessionalService) -> ProfessionalService:
        row = mappers.professional_service_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.professional_service_to_domain(merged)

    def get_by_id(self, entity_id: str) -> ProfessionalService | None:
        row = self._session.get(ProfessionalServiceRow, entity_id)
        if row is None:
            return None
        return mappers.professional_service_to_domain(row)

    def list_by_source_document_id(
        self, source_document_id: str
    ) -> list[ProfessionalService]:
        stmt = (
            select(ProfessionalServiceRow)
            .where(ProfessionalServiceRow.source_document_id == source_document_id)
            .order_by(ProfessionalServiceRow.id)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.professional_service_to_domain(row) for row in rows]


class CapabilityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: Capability) -> Capability:
        row = mappers.capability_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.capability_to_domain(merged)

    def get_by_id(self, entity_id: str) -> Capability | None:
        row = self._session.get(CapabilityRow, entity_id)
        if row is None:
            return None
        return mappers.capability_to_domain(row)

    def get_by_code(self, code: str) -> Capability | None:
        stmt = select(CapabilityRow).where(CapabilityRow.code == code)
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        return mappers.capability_to_domain(row)


class AssignmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: Assignment) -> Assignment:
        row = mappers.assignment_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.assignment_to_domain(merged)

    def get_by_id(self, entity_id: str) -> Assignment | None:
        row = self._session.get(AssignmentRow, entity_id)
        if row is None:
            return None
        return mappers.assignment_to_domain(row)

    def list_by_source_document_id(self, source_document_id: str) -> list[Assignment]:
        stmt = (
            select(AssignmentRow)
            .where(AssignmentRow.source_document_id == source_document_id)
            .order_by(AssignmentRow.id)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.assignment_to_domain(row) for row in rows]


class AssignmentCapabilityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: AssignmentCapability) -> AssignmentCapability:
        row = mappers.assignment_capability_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.assignment_capability_to_domain(merged)

    def get_by_id(self, entity_id: str) -> AssignmentCapability | None:
        row = self._session.get(AssignmentCapabilityRow, entity_id)
        if row is None:
            return None
        return mappers.assignment_capability_to_domain(row)

    def list_for_assignment(self, assignment_id: str) -> list[AssignmentCapability]:
        stmt = (
            select(AssignmentCapabilityRow)
            .where(AssignmentCapabilityRow.assignment_id == assignment_id)
            .order_by(AssignmentCapabilityRow.id)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.assignment_capability_to_domain(row) for row in rows]


class SkillRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: Skill) -> Skill:
        row = mappers.skill_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.skill_to_domain(merged)

    def get_by_id(self, entity_id: str) -> Skill | None:
        row = self._session.get(SkillRow, entity_id)
        if row is None:
            return None
        return mappers.skill_to_domain(row)

    def list_by_source_document_id(self, source_document_id: str) -> list[Skill]:
        stmt = (
            select(SkillRow)
            .where(SkillRow.source_document_id == source_document_id)
            .order_by(SkillRow.name)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.skill_to_domain(row) for row in rows]


class CountryExperienceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: CountryExperience) -> CountryExperience:
        row = mappers.country_experience_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.country_experience_to_domain(merged)

    def get_by_id(self, entity_id: str) -> CountryExperience | None:
        row = self._session.get(CountryExperienceRow, entity_id)
        if row is None:
            return None
        return mappers.country_experience_to_domain(row)

    def list_by_source_document_id(
        self, source_document_id: str
    ) -> list[CountryExperience]:
        stmt = (
            select(CountryExperienceRow)
            .where(CountryExperienceRow.source_document_id == source_document_id)
            .order_by(CountryExperienceRow.country)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.country_experience_to_domain(row) for row in rows]


class LanguageCapabilityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: LanguageCapability) -> LanguageCapability:
        row = mappers.language_capability_to_row(entity)
        merged = self._session.merge(row)
        self._session.flush()
        return mappers.language_capability_to_domain(merged)

    def get_by_id(self, entity_id: str) -> LanguageCapability | None:
        row = self._session.get(LanguageCapabilityRow, entity_id)
        if row is None:
            return None
        return mappers.language_capability_to_domain(row)

    def list_by_source_document_id(
        self, source_document_id: str
    ) -> list[LanguageCapability]:
        stmt = (
            select(LanguageCapabilityRow)
            .where(LanguageCapabilityRow.source_document_id == source_document_id)
            .order_by(LanguageCapabilityRow.language)
        )
        rows = self._session.scalars(stmt).all()
        return [mappers.language_capability_to_domain(row) for row in rows]
