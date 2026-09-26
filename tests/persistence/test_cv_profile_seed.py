"""PostgreSQL integration tests for CV profile seeding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.domain import Skill
from jobhunter.infrastructure.importers.cv_profile import CvProfileSeeder
from jobhunter.infrastructure.importers.cv_profile.identity import (
    profile_document_id,
    skill_id,
)
from jobhunter.infrastructure.importers.professional_services import (
    ProfessionalServicesSeeder,
)
from jobhunter.infrastructure.importers.professional_services.identity import (
    professional_profile_id,
)
from jobhunter.infrastructure.persistence.profile_models import (
    CountryExperienceRow,
    LanguageCapabilityRow,
    ProfileDocumentRow,
    SkillRow,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    ProfessionalProfileRepository,
    SkillRepository,
)

pytestmark = pytest.mark.integration

SYNTH_SERVICES = (
    Path(__file__).resolve().parents[1] / "seeds" / "synthetic_professional_services.json"
)
SYNTH_CV = Path(__file__).resolve().parents[1] / "seeds" / "synthetic_cv_profile.json"


def _cv_ref() -> str:
    return json.loads(SYNTH_CV.read_text(encoding="utf-8"))["source_reference"]


def test_dry_run_writes_nothing(db_session: Session) -> None:
    before = db_session.scalar(select(func.count()).select_from(SkillRow)) or 0
    report = CvProfileSeeder(db_session).run(SYNTH_CV, apply=False)
    assert not report.has_errors()
    after = db_session.scalar(select(func.count()).select_from(SkillRow)) or 0
    assert before == after
    assert report.skills_created == 3


def test_validation_failure_does_not_apply(
    db_session: Session, tmp_path: Path,
) -> None:
    bad = json.loads(SYNTH_CV.read_text(encoding="utf-8"))
    bad["languages"] = bad["languages"][:2]
    bad_path = tmp_path / "invalid.json"
    bad_path.write_text(json.dumps(bad), encoding="utf-8")
    before = db_session.scalar(select(func.count()).select_from(SkillRow)) or 0
    report = CvProfileSeeder(db_session).run(bad_path, apply=True)
    assert report.has_errors()
    assert not report.applied
    after = db_session.scalar(select(func.count()).select_from(SkillRow)) or 0
    assert before == after


def test_apply_preserves_positioning_and_sets_primary_cv(db_session: Session) -> None:
    ProfessionalServicesSeeder(db_session).run(SYNTH_SERVICES, apply=True)
    profiles = ProfessionalProfileRepository(db_session)
    before = profiles.get_by_id(professional_profile_id())
    assert before is not None
    positioning = before.positioning_summary

    report = CvProfileSeeder(db_session).run(SYNTH_CV, apply=True)
    assert not report.has_errors()
    assert report.applied

    after = profiles.get_by_id(professional_profile_id())
    assert after is not None
    assert after.positioning_summary == positioning
    assert after.primary_cv_document_id == profile_document_id(_cv_ref())


def test_apply_idempotent_and_provenance(db_session: Session) -> None:
    seeder = CvProfileSeeder(db_session)
    first = seeder.run(SYNTH_CV, apply=True)
    assert not first.has_errors()
    doc_id = profile_document_id(_cv_ref())

    skill_count = (
        db_session.scalar(
            select(func.count())
            .select_from(SkillRow)
            .where(SkillRow.source_document_id == doc_id)
        )
        or 0
    )
    assert skill_count == 3

    loaded = SkillRepository(db_session).get_by_id(skill_id(_cv_ref(), "syn-skill-a"))
    assert loaded is not None
    assert loaded.cv_emphasized is True
    assert loaded.source_document_id == doc_id

    second = seeder.run(SYNTH_CV, apply=False)
    assert not second.has_errors()
    assert second.skills_created == 0
    assert second.skills_unchanged == 3


def test_source_scoped_skill_removal(db_session: Session, tmp_path: Path) -> None:
    path = tmp_path / "evolving.json"
    path.write_text(SYNTH_CV.read_text(encoding="utf-8"), encoding="utf-8")
    seeder = CvProfileSeeder(db_session)
    seeder.run(path, apply=True)

    data = json.loads(path.read_text(encoding="utf-8"))
    data["skills"] = [s for s in data["skills"] if s["key"] != "syn-skill-c"]
    path.write_text(json.dumps(data), encoding="utf-8")

    report = seeder.run(path, apply=True)
    assert not report.has_errors()
    assert report.skills_deleted == 1

    ref = data["source_reference"]
    assert SkillRepository(db_session).get_by_id(skill_id(ref, "syn-skill-c")) is None


def test_unrelated_skill_untouched(db_session: Session) -> None:
    repo = SkillRepository(db_session)
    other = repo.save(
        Skill(
            id="other-skill-manual",
            name="Manual unrelated skill",
            category="manual",
            source_document_id=None,
        )
    )
    CvProfileSeeder(db_session).run(SYNTH_CV, apply=True)
    assert repo.get_by_id(other.id) == other


def test_profile_document_not_duplicated(db_session: Session) -> None:
    CvProfileSeeder(db_session).run(SYNTH_CV, apply=True)
    doc_id = profile_document_id(_cv_ref())
    count = (
        db_session.scalar(
            select(func.count())
            .select_from(ProfileDocumentRow)
            .where(ProfileDocumentRow.id == doc_id)
        )
        or 0
    )
    assert count == 1


def test_country_and_language_counts(db_session: Session) -> None:
    CvProfileSeeder(db_session).run(SYNTH_CV, apply=True)
    doc_id = profile_document_id(_cv_ref())
    lang_count = (
        db_session.scalar(
            select(func.count())
            .select_from(LanguageCapabilityRow)
            .where(LanguageCapabilityRow.source_document_id == doc_id)
        )
        or 0
    )
    country_count = (
        db_session.scalar(
            select(func.count())
            .select_from(CountryExperienceRow)
            .where(CountryExperienceRow.source_document_id == doc_id)
        )
        or 0
    )
    assert lang_count == 5
    assert country_count == 31
