"""Tests for lifecycle resolution rules."""

from __future__ import annotations

from datetime import date

from jobhunter.domain.enums import LifecycleStatus
from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity_lifecycle import resolve_lifecycle_status


def _norm(**kwargs) -> NormalizedOpportunity:
    return NormalizedOpportunity(title="Test", **kwargs)


def test_new_opportunity() -> None:
    status = resolve_lifecycle_status(
        is_new_opportunity=True,
        has_material_changes=False,
        normalized=_norm(deadline=date(2026, 12, 31)),
        as_of=date(2026, 6, 1),
    )
    assert status is LifecycleStatus.NEW


def test_still_open_without_changes() -> None:
    status = resolve_lifecycle_status(
        is_new_opportunity=False,
        has_material_changes=False,
        normalized=_norm(deadline=date(2026, 12, 31)),
        as_of=date(2026, 6, 1),
    )
    assert status is LifecycleStatus.STILL_OPEN


def test_updated_with_material_changes() -> None:
    status = resolve_lifecycle_status(
        is_new_opportunity=False,
        has_material_changes=True,
        normalized=_norm(deadline=date(2026, 12, 31)),
        as_of=date(2026, 6, 1),
    )
    assert status is LifecycleStatus.UPDATED


def test_expired_deadline() -> None:
    status = resolve_lifecycle_status(
        is_new_opportunity=False,
        has_material_changes=True,
        normalized=_norm(deadline=date(2026, 1, 1)),
        as_of=date(2026, 6, 1),
    )
    assert status is LifecycleStatus.EXPIRED


def test_closed_from_source_status() -> None:
    status = resolve_lifecycle_status(
        is_new_opportunity=False,
        has_material_changes=False,
        normalized=_norm(source_status="closed"),
        as_of=date(2026, 6, 1),
    )
    assert status is LifecycleStatus.CLOSED
