"""PostgreSQL integration tests for professional evidence persistence."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentCapabilityRepository,
    AssignmentRepository,
    CapabilityRepository,
    LanguageCapabilityRepository,
    ProfessionalProfileRepository,
    ProfessionalServiceRepository,
    ProfileDocumentRepository,
    SkillRepository,
)

pytestmark = pytest.mark.integration


def test_profile_document_round_trip(db_session: Session) -> None:
    repo = ProfileDocumentRepository(db_session)
    doc = ProfileDocument(
        id="pdoc-1",
        document_type=ProfileDocumentType.PROJECT_DATA,
        title="Synthetic project data",
        source_reference="fixtures/synthetic_projects.xlsx",
    )
    repo.save(doc)
    loaded = repo.get_by_id("pdoc-1")
    assert loaded == doc


def test_professional_profile_with_primary_cv_document(db_session: Session) -> None:
    docs = ProfileDocumentRepository(db_session)
    profiles = ProfessionalProfileRepository(db_session)
    cv_doc = docs.save(
        ProfileDocument(
            id="pdoc-cv",
            document_type=ProfileDocumentType.CV,
            title="Synthetic CV",
        )
    )
    profile = ProfessionalProfile(
        id="prof-1",
        display_name="Example Consultant",
        positioning_summary="Geo-ICT",
        primary_cv_document_id=cv_doc.id,
    )
    profiles.save(profile)
    loaded = profiles.get_by_id("prof-1")
    assert loaded is not None
    assert loaded.primary_cv_document_id == cv_doc.id


def test_professional_service_round_trip_and_provenance(db_session: Session) -> None:
    docs = ProfileDocumentRepository(db_session)
    services = ProfessionalServiceRepository(db_session)
    doc = docs.save(
        ProfileDocument(
            id="pdoc-svc",
            document_type=ProfileDocumentType.PROFESSIONAL_SERVICES,
            title="Synthetic services",
        )
    )
    service = ProfessionalService(
        id="svc-1",
        name="Example GIS service",
        description="Synthetic",
        is_active=True,
        source_document_id=doc.id,
    )
    services.save(service)
    loaded = services.get_by_id("svc-1")
    assert loaded == service


def test_capability_round_trip_category_and_code(db_session: Session) -> None:
    repo = CapabilityRepository(db_session)
    cap = Capability(
        id="cap-1",
        code="test-cap-round-trip",
        name="System integration and interoperability",
        category=CapabilityCategory.SYSTEM_DEVELOPMENT,
    )
    repo.save(cap)
    by_id = repo.get_by_id("cap-1")
    by_code = repo.get_by_code("test-cap-round-trip")
    assert by_id == cap
    assert by_code == cap


def test_capability_unique_code_constraint(db_session: Session) -> None:
    repo = CapabilityRepository(db_session)
    repo.save(
        Capability(
            id="cap-a",
            code="test-cap-dup",
            name="Land Administration",
            category=CapabilityCategory.DOMAIN,
        )
    )
    db_session.flush()
    duplicate = Capability(
        id="cap-b",
        code="test-cap-dup",
        name="Duplicate code",
        category=CapabilityCategory.DOMAIN,
    )
    with pytest.raises(IntegrityError):
        repo.save(duplicate)
        db_session.flush()
    db_session.rollback()


def test_assignment_period_text_and_working_days(db_session: Session) -> None:
    docs = ProfileDocumentRepository(db_session)
    assignments = AssignmentRepository(db_session)
    doc = docs.save(
        ProfileDocument(
            id="pdoc-asg",
            document_type=ProfileDocumentType.PROJECT_DATA,
            title="Projects",
        )
    )
    assignment = Assignment(
        id="asg-1",
        project_name="Synthetic cadastre project",
        period_text="2019–2021",
        working_days=95,
        source_document_id=doc.id,
    )
    assignments.save(assignment)
    loaded = assignments.get_by_id("asg-1")
    assert loaded is not None
    assert loaded.period_text == "2019–2021"
    assert loaded.working_days == 95
    assert loaded.source_document_id == doc.id


def test_assignment_capability_links_and_uniqueness(db_session: Session) -> None:
    docs = ProfileDocumentRepository(db_session)
    assignments = AssignmentRepository(db_session)
    capabilities = CapabilityRepository(db_session)
    links = AssignmentCapabilityRepository(db_session)

    doc = docs.save(
        ProfileDocument(
            id="pdoc-link",
            document_type=ProfileDocumentType.PROJECT_DATA,
            title="Projects",
        )
    )
    assignment = assignments.save(
        Assignment(id="asg-m", project_name="Multi-cap project")
    )
    cap_one = capabilities.save(
        Capability(
            id="cap-gis",
            code="test-cap-gis",
            name="GIS development",
            category=CapabilityCategory.SYSTEM_TYPE,
        )
    )
    cap_two = capabilities.save(
        Capability(
            id="cap-etl",
            code="test-cap-etl",
            name="Data integration",
            category=CapabilityCategory.DATA_ANALYSIS,
        )
    )

    links.save(
        AssignmentCapability(
            id="link-1",
            assignment_id=assignment.id,
            capability_id=cap_one.id,
            source_document_id=doc.id,
        )
    )
    links.save(
        AssignmentCapability(
            id="link-2",
            assignment_id=assignment.id,
            capability_id=cap_two.id,
        )
    )
    listed = links.list_for_assignment(assignment.id)
    assert {item.capability_id for item in listed} == {cap_one.id, cap_two.id}

    other_assignment = assignments.save(
        Assignment(id="asg-other", project_name="Other project")
    )
    links.save(
        AssignmentCapability(
            id="link-3",
            assignment_id=other_assignment.id,
            capability_id=cap_one.id,
        )
    )

    duplicate = AssignmentCapability(
        id="link-dup",
        assignment_id=assignment.id,
        capability_id=cap_one.id,
    )
    with pytest.raises(IntegrityError):
        links.save(duplicate)
        db_session.flush()
    db_session.rollback()


def test_skill_and_language_round_trip_nullable_provenance(
    db_session: Session,
) -> None:
    skills = SkillRepository(db_session)
    languages = LanguageCapabilityRepository(db_session)

    skill = skills.save(Skill(id="skill-1", name="PostgreSQL"))
    lang = languages.save(
        LanguageCapability(
            id="lang-1",
            language="English",
            proficiency_text="Professional working proficiency",
        )
    )
    assert skills.get_by_id("skill-1") == skill
    assert languages.get_by_id("lang-1") == lang
    assert skill.source_document_id is None
