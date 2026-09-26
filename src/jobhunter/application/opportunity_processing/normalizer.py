"""Normalizer contract for RawOpportunity -> NormalizedOpportunity."""

from __future__ import annotations

from typing import Protocol

from jobhunter.domain.normalized_opportunity import NormalizedOpportunity
from jobhunter.domain.raw_opportunity import RawOpportunity


class OpportunityNormalizer(Protocol):
    def normalize(self, raw: RawOpportunity) -> NormalizedOpportunity:
        """Map raw source fields into a normalized snapshot."""
