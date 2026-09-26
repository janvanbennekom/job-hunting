"""Unit tests for Professional Services seed loading and validation."""

from pathlib import Path

from jobhunter.infrastructure.importers.professional_services.loader import load_seed
from jobhunter.infrastructure.importers.professional_services.validation import (
    validate_seed,
)


def test_load_curated_seed_has_nine_services() -> None:
    root = Path(__file__).resolve().parents[2]
    seed = load_seed(
        root / "data/seeds/professional_services_jan_van_bennekom-minnema_uk.json"
    )
    assert seed.schema_version == 1
    assert len(seed.services) == 9
    assert seed.source_reference.endswith(
        "professional_services_jan_van_bennekom-minnema_uk.pdf"
    )
    assert not validate_seed(seed)


def test_duplicate_service_key_fails_validation(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        """
{
  "schema_version": 1,
  "source_reference": "tests/bad.json",
  "source_document": {"title": "T"},
  "professional_profile": {"display_name": "X"},
  "services": [
    {"key": "dup", "name": "A", "description": "a"},
    {"key": "dup", "name": "B", "description": "b"}
  ]
}
""",
        encoding="utf-8",
    )
    seed = load_seed(path)
    errors = validate_seed(seed)
    assert any("Duplicate service key" in e for e in errors)
