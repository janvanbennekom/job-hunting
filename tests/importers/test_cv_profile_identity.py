"""Deterministic CV profile seed identifiers."""

from __future__ import annotations

from jobhunter.infrastructure.importers.cv_profile.identity import (
    language_capability_id,
    skill_id,
)


def test_skill_id_is_stable() -> None:
    ref = "docs/cv.pdf"
    a = skill_id(ref, "python")
    b = skill_id(ref, "python")
    assert a == b
    assert skill_id(ref, "Python") == a


def test_language_capability_id_is_stable() -> None:
    ref = "tests/seeds/synthetic_cv_profile.json"
    assert language_capability_id(ref, "dutch") == language_capability_id(ref, "dutch")
