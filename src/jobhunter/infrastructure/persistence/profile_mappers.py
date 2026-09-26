"""Domain ↔ persistence mapping for professional evidence."""

from __future__ import annotations

from jobhunter.domain import (
    Assignment,
    AssignmentCapability,
    Capability,
    LanguageCapability,
    ProfessionalProfile,
    ProfessionalService,
    ProfileDocument,
    Skill,
)
from jobhunter.domain.profile_enums import CapabilityCategory, ProfileDocumentType
from jobhunter.infrastructure.persistence.profile_models import (
    AssignmentCapabilityRow,
    AssignmentRow,
    CapabilityRow,
    LanguageCapabilityRow,
    ProfessionalProfileRow,
    ProfessionalServiceRow,
    ProfileDocumentRow,
    SkillRow,
)


def profile_document_to_row(entity: ProfileDocument) -> ProfileDocumentRow:
    return ProfileDocumentRow(
        id=entity.id,
        document_type=entity.document_type.value,
        title=entity.title,
        source_reference=entity.source_reference,
        version_label=entity.version_label,
        notes=entity.notes,
    )


def profile_document_to_domain(row: ProfileDocumentRow) -> ProfileDocument:
    return ProfileDocument(
        id=row.id,
        document_type=ProfileDocumentType(row.document_type),
        title=row.title,
        source_reference=row.source_reference,
        version_label=row.version_label,
        notes=row.notes,
    )


def professional_profile_to_row(entity: ProfessionalProfile) -> ProfessionalProfileRow:
    return ProfessionalProfileRow(
        id=entity.id,
        display_name=entity.display_name,
        positioning_summary=entity.positioning_summary,
        primary_cv_document_id=entity.primary_cv_document_id,
    )


def professional_profile_to_domain(row: ProfessionalProfileRow) -> ProfessionalProfile:
    return ProfessionalProfile(
        id=row.id,
        display_name=row.display_name,
        positioning_summary=row.positioning_summary,
        primary_cv_document_id=row.primary_cv_document_id,
    )


def professional_service_to_row(entity: ProfessionalService) -> ProfessionalServiceRow:
    return ProfessionalServiceRow(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        is_active=entity.is_active,
        source_document_id=entity.source_document_id,
    )


def professional_service_to_domain(row: ProfessionalServiceRow) -> ProfessionalService:
    return ProfessionalService(
        id=row.id,
        name=row.name,
        description=row.description,
        is_active=row.is_active,
        source_document_id=row.source_document_id,
    )


def capability_to_row(entity: Capability) -> CapabilityRow:
    return CapabilityRow(
        id=entity.id,
        code=entity.code,
        name=entity.name,
        category=entity.category.value,
        description=entity.description,
        is_active=entity.is_active,
        source_document_id=entity.source_document_id,
    )


def capability_to_domain(row: CapabilityRow) -> Capability:
    return Capability(
        id=row.id,
        code=row.code,
        name=row.name,
        category=CapabilityCategory(row.category),
        description=row.description,
        is_active=row.is_active,
        source_document_id=row.source_document_id,
    )


def assignment_to_row(entity: Assignment) -> AssignmentRow:
    return AssignmentRow(
        id=entity.id,
        source_record_id=entity.source_record_id,
        sequence=entity.sequence,
        project_name=entity.project_name,
        role=entity.role,
        beneficiary=entity.beneficiary,
        donor=entity.donor,
        country=entity.country,
        period_text=entity.period_text,
        working_days=entity.working_days,
        last_active_year=entity.last_active_year,
        description=entity.description,
        responsibilities=entity.responsibilities,
        tools_technologies_text=entity.tools_technologies_text,
        web_link=entity.web_link,
        source_document_id=entity.source_document_id,
    )


def assignment_to_domain(row: AssignmentRow) -> Assignment:
    return Assignment(
        id=row.id,
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
        source_document_id=row.source_document_id,
    )


def assignment_capability_to_row(
    entity: AssignmentCapability,
) -> AssignmentCapabilityRow:
    return AssignmentCapabilityRow(
        id=entity.id,
        assignment_id=entity.assignment_id,
        capability_id=entity.capability_id,
        source_document_id=entity.source_document_id,
    )


def assignment_capability_to_domain(
    row: AssignmentCapabilityRow,
) -> AssignmentCapability:
    return AssignmentCapability(
        id=row.id,
        assignment_id=row.assignment_id,
        capability_id=row.capability_id,
        source_document_id=row.source_document_id,
    )


def skill_to_row(entity: Skill) -> SkillRow:
    return SkillRow(
        id=entity.id,
        name=entity.name,
        category=entity.category,
        description=entity.description,
        source_document_id=entity.source_document_id,
    )


def skill_to_domain(row: SkillRow) -> Skill:
    return Skill(
        id=row.id,
        name=row.name,
        category=row.category,
        description=row.description,
        source_document_id=row.source_document_id,
    )


def language_capability_to_row(entity: LanguageCapability) -> LanguageCapabilityRow:
    return LanguageCapabilityRow(
        id=entity.id,
        language=entity.language,
        proficiency_text=entity.proficiency_text,
        cefr_level=entity.cefr_level,
        notes=entity.notes,
        source_document_id=entity.source_document_id,
    )


def language_capability_to_domain(row: LanguageCapabilityRow) -> LanguageCapability:
    return LanguageCapability(
        id=row.id,
        language=row.language,
        proficiency_text=row.proficiency_text,
        cefr_level=row.cefr_level,
        notes=row.notes,
        source_document_id=row.source_document_id,
    )
