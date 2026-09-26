"""PostgreSQL integration tests for Professional Services seeding."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jobhunter.domain import ProfessionalService
from jobhunter.infrastructure.importers.professional_services import (
    ProfessionalServicesSeeder,
)
from jobhunter.infrastructure.importers.professional_services.identity import (
    professional_service_id,
    profile_document_id,
)
from jobhunter.infrastructure.persistence.profile_models import (
    ProfessionalServiceRow,
    ProfileDocumentRow,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    ProfessionalServiceRepository,
)

pytestmark = pytest.mark.integration

SYNTH_SEED = (
    Path(__file__).resolve().parents[1] / "seeds" / "synthetic_professional_services.json"
)


def test_dry_run_writes_nothing(db_session: Session) -> None:
    before = db_session.scalar(select(func.count()).select_from(ProfessionalServiceRow)) or 0
    report = ProfessionalServicesSeeder(db_session).run(SYNTH_SEED, apply=False)
    assert not report.has_errors()
    after = db_session.scalar(select(func.count()).select_from(ProfessionalServiceRow)) or 0
    assert before == after
    assert report.professional_services_created == 2


def test_apply_and_rerun_is_idempotent(db_session: Session) -> None:
    seeder = ProfessionalServicesSeeder(db_session)
    first = seeder.run(SYNTH_SEED, apply=True)
    assert not first.has_errors()
    assert first.professional_services_created == 2

    second = seeder.run(SYNTH_SEED, apply=False)
    assert not second.has_errors()
    assert second.professional_services_created == 0
    assert second.professional_services_updated == 0
    assert second.professional_services_unchanged == 2


def test_updated_description_and_removed_service_deactivation(
    db_session: Session, tmp_path: Path,
) -> None:
    path = tmp_path / "evolving.json"
    path.write_text(SYNTH_SEED.read_text(encoding="utf-8"), encoding="utf-8")
    seeder = ProfessionalServicesSeeder(db_session)
    seeder.run(path, apply=True)

    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    data["services"] = [
        {
            "key": "syn-service-a",
            "name": "Synthetic Service A",
            "description": "Updated description.",
            "is_active": True,
        }
    ]
    path.write_text(json.dumps(data), encoding="utf-8")

    report = seeder.run(path, apply=True)
    assert not report.has_errors()
    assert report.professional_services_updated >= 1
    assert report.professional_services_deactivated >= 1

    repo = ProfessionalServiceRepository(db_session)
    import json

    ref = json.loads(path.read_text(encoding="utf-8"))["source_reference"]
    b = repo.get_by_id(professional_service_id(ref, "syn-service-b"))
    assert b is not None
    assert b.is_active is False


def test_unrelated_service_not_modified(db_session: Session) -> None:
    repo = ProfessionalServiceRepository(db_session)
    other = repo.save(
        ProfessionalService(
            id="other-service-manual",
            name="Manual unrelated service",
            description="From another source",
            source_document_id=None,
        )
    )
    seeder = ProfessionalServicesSeeder(db_session)
    seeder.run(SYNTH_SEED, apply=True)
    loaded = repo.get_by_id(other.id)
    assert loaded == other


def test_profile_document_not_duplicated(db_session: Session) -> None:
    seeder = ProfessionalServicesSeeder(db_session)
    seeder.run(SYNTH_SEED, apply=True)
    import json

    ref = json.loads(SYNTH_SEED.read_text(encoding="utf-8"))["source_reference"]
    doc_id = profile_document_id(ref)
    count = (
        db_session.scalar(
            select(func.count())
            .select_from(ProfileDocumentRow)
            .where(ProfileDocumentRow.id == doc_id)
        )
        or 0
    )
    assert count == 1
