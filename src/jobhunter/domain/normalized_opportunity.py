"""Normalized opportunity snapshot produced from raw source data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from jobhunter.domain.enums import OpportunityType


@dataclass(slots=True)
class NormalizedOpportunity:
    """Source-independent normalized fields before persistence identity is applied."""

    title: str
    organisation: str | None = None
    location: str | None = None
    description: str | None = None
    publication_date: date | None = None
    deadline: date | None = None
    expected_start_date: date | None = None
    opportunity_type: OpportunityType = OpportunityType.UNKNOWN
    source_status: str | None = None
