"""Detect material field changes between normalized snapshots."""

from __future__ import annotations

from datetime import date

from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_change import OpportunityChange
from jobhunter.domain.opportunity_enums import MaterialChangeField


def _format_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def detect_material_changes(
    previous: Opportunity,
    incoming: NormalizedOpportunity,
) -> list[tuple[MaterialChangeField, str | None, str | None]]:
    """Return tuples of (field, previous_value, new_value) for material differences."""
    changes: list[tuple[MaterialChangeField, str | None, str | None]] = []

    prev_title = _normalize_text(previous.title)
    new_title = _normalize_text(incoming.title)
    if prev_title != new_title:
        changes.append(
            (MaterialChangeField.TITLE, prev_title, new_title)
        )

    prev_deadline = _format_date(previous.deadline)
    new_deadline = _format_date(incoming.deadline)
    if prev_deadline != new_deadline:
        changes.append(
            (MaterialChangeField.DEADLINE, prev_deadline, new_deadline)
        )

    prev_desc = _normalize_text(previous.description)
    new_desc = _normalize_text(incoming.description)
    if prev_desc != new_desc:
        changes.append(
            (MaterialChangeField.DESCRIPTION, prev_desc, new_desc)
        )

    prev_loc = _normalize_text(previous.location)
    new_loc = _normalize_text(incoming.location)
    if prev_loc != new_loc:
        changes.append(
            (MaterialChangeField.LOCATION, prev_loc, new_loc)
        )

    prev_status = _normalize_text(previous.source_status)
    new_status = _normalize_text(incoming.source_status)
    if prev_status != new_status:
        changes.append(
            (MaterialChangeField.SOURCE_STATUS, prev_status, new_status)
        )

    return changes


def build_change_records(
    opportunity_id: str,
    observation_id: str,
    observed_at,
    deltas: list[tuple[MaterialChangeField, str | None, str | None]],
) -> list[OpportunityChange]:
    return [
        OpportunityChange(
            opportunity_id=opportunity_id,
            observation_id=observation_id,
            field_name=field,
            previous_value=previous,
            new_value=new_value,
            observed_at=observed_at,
        )
        for field, previous, new_value in deltas
    ]
