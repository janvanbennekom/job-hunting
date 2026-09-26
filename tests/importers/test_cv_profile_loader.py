"""CV profile seed loader."""

from __future__ import annotations

from pathlib import Path

from jobhunter.infrastructure.importers.cv_profile.loader import load_seed

SYNTH = Path(__file__).resolve().parents[1] / "seeds" / "synthetic_cv_profile.json"


def test_load_synthetic_seed() -> None:
    seed = load_seed(SYNTH)
    assert seed.schema_version == 1
    assert len(seed.skills) == 3
    assert len(seed.languages) == 5
    assert len(seed.countries) == 31
    assert seed.skills[0].cv_emphasized is True
