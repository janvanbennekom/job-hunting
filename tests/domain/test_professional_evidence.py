"""Tests for Phase 3A professional evidence domain."""

import pytest

from jobhunter.domain import (
    Assignment,
    AssignmentCapability,
    Capability,
    CapabilityCategory,
    LanguageCapability,
    ProfessionalProfile,
    ProfessionalService,
    ProfileDocument,
    ProfileDocumentType,
    Skill,
)


def test_professional_profile_construction() -> None:
    profile = ProfessionalProfile(
        id="prof-1",
        display_name="Example Consultant",
        positioning_summary="Geo-ICT specialist",
        primary_cv_document_id="doc-cv-1",
    )
    assert profile.display_name == "Example Consultant"
    assert profile.primary_cv_document_id == "doc-cv-1"


def test_professional_service_active_state_and_provenance() -> None:
    doc_id = "doc-services-1"
    service = ProfessionalService(
        id="svc-1",
        name="GIS Implementation",
        description="Enterprise GIS delivery",
        is_active=False,
        source_document_id=doc_id,
    )
    assert service.is_active is False
    assert service.source_document_id == doc_id
    restored = ProfessionalService.from_mapping(service.to_mapping())
    assert restored == service


def test_capability_category_values() -> None:
    assert CapabilityCategory.DOMAIN.value == "DOMAIN"
    assert CapabilityCategory.SYSTEM_DEVELOPMENT.value == "SYSTEM_DEVELOPMENT"
    assert len(CapabilityCategory) == 7


def test_capability_code_and_category_distinction() -> None:
    integration = Capability(
        id="cap-1",
        code="fsd-API",
        name="System integration and interoperability",
        category=CapabilityCategory.SYSTEM_DEVELOPMENT,
        description="Integration across systems",
    )
    land_admin = Capability(
        id="cap-2",
        code="fd-LA",
        name="Land Administration",
        category=CapabilityCategory.DOMAIN,
    )
    assert integration.code == "fsd-API"
    assert land_admin.category is CapabilityCategory.DOMAIN
    assert integration.category is not CapabilityCategory.DOMAIN
    restored = Capability.from_mapping(integration.to_mapping())
    assert restored == integration


def test_capability_rejects_empty_code() -> None:
    with pytest.raises(ValueError, match="code"):
        Capability(
            code="  ",
            name="Example",
            category=CapabilityCategory.DOMAIN,
        )


def test_assignment_representative_metadata() -> None:
    doc_id = "doc-project-data"
    assignment = Assignment(
        id="asg-1",
        source_record_id="42",
        sequence=3,
        project_name="National cadastre modernisation",
        role="GIS team leader",
        beneficiary="National mapping agency",
        donor="Example donor",
        country="Example country",
        period_text="2019–2021",
        working_days=120,
        last_active_year=2021,
        description="Implementation support",
        responsibilities="Technical leadership",
        tools_technologies_text="PostgreSQL, QGIS",
        web_link="https://example.org/project",
        source_document_id=doc_id,
    )
    assert assignment.period_text == "2019–2021"
    assert assignment.tools_technologies_text == "PostgreSQL, QGIS"
    assert assignment.source_document_id == doc_id
    restored = Assignment.from_mapping(assignment.to_mapping())
    assert restored == assignment


def test_assignment_optional_fields() -> None:
    assignment = Assignment(project_name="Minimal project")
    assert assignment.role is None
    assert assignment.working_days is None


def test_assignment_rejects_negative_working_days() -> None:
    with pytest.raises(ValueError, match="working_days"):
        Assignment(project_name="P", working_days=-1)


def test_assignment_capability_many_to_many_concept() -> None:
    assignment = Assignment(id="asg-a", project_name="Project A")
    cap_gis = Capability(
        id="cap-gis",
        code="fsd-GIS",
        name="GIS development",
        category=CapabilityCategory.SYSTEM_TYPE,
    )
    cap_qa = Capability(
        id="cap-qa",
        code="fqa-BPR",
        name="Business process modelling",
        category=CapabilityCategory.QUALITY_ASSURANCE,
    )
    link_one = AssignmentCapability(
        id="link-1",
        assignment_id=assignment.id,
        capability_id=cap_gis.id,
        source_document_id="doc-project",
    )
    link_two = AssignmentCapability(
        id="link-2",
        assignment_id=assignment.id,
        capability_id=cap_qa.id,
        source_document_id="doc-project",
    )
    shared_capability = Capability(
        id="cap-shared",
        code="fda-ETL",
        name="Data integration",
        category=CapabilityCategory.DATA_ANALYSIS,
    )
    other_assignment = Assignment(id="asg-b", project_name="Project B")
    link_three = AssignmentCapability(
        assignment_id=other_assignment.id,
        capability_id=shared_capability.id,
    )
    link_four = AssignmentCapability(
        assignment_id=assignment.id,
        capability_id=shared_capability.id,
    )

    assert link_one.assignment_id == link_two.assignment_id
    assert link_one.capability_id != link_two.capability_id
    assert link_three.capability_id == link_four.capability_id
    assert link_three.assignment_id != link_four.assignment_id


def test_skill_construction() -> None:
    skill = Skill(
        id="skill-1",
        name="PostgreSQL",
        category="database",
        source_document_id="doc-cv",
    )
    assert skill.name == "PostgreSQL"
    restored = Skill.from_mapping(skill.to_mapping())
    assert restored == skill


def test_language_capability_without_cefr() -> None:
    lang = LanguageCapability(
        id="lang-1",
        language="English",
        proficiency_text="Professional working proficiency",
        notes="Used in international assignments",
    )
    assert lang.cefr_level is None
    restored = LanguageCapability.from_mapping(lang.to_mapping())
    assert restored == lang


def test_profile_document_types() -> None:
    cv = ProfileDocument(
        id="doc-1",
        document_type=ProfileDocumentType.CV,
        title="Detailed CV",
        source_reference="docs/example_cv.pdf",
    )
    sheet = ProfileDocument(
        document_type=ProfileDocumentType.PROJECT_DATA,
        title="Project spreadsheet",
        source_reference="docs/example_projects.xlsx",
    )
    assert cv.document_type is ProfileDocumentType.CV
    assert sheet.document_type is ProfileDocumentType.PROJECT_DATA
    restored = ProfileDocument.from_mapping(cv.to_mapping())
    assert restored == cv


def test_professional_service_is_not_capability() -> None:
    service = ProfessionalService(name="LIS Implementation")
    capability = Capability(
        code="fsd-LIS",
        name="Land information system development",
        category=CapabilityCategory.SYSTEM_TYPE,
    )
    assert service.name != capability.name
    assert not hasattr(service, "code")


def test_capability_is_not_skill() -> None:
    capability = Capability(
        code="fsd-API",
        name="System integration and interoperability",
        category=CapabilityCategory.SYSTEM_DEVELOPMENT,
    )
    skill = Skill(name="GeoServer")
    assert capability.code != skill.name
