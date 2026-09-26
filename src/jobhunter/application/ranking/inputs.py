"""Resolved inputs for ranking calculation."""

from __future__ import annotations

from dataclasses import dataclass

from jobhunter.domain.eligibility_decision import EligibilityDecision
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.search_theme import SearchTheme
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
)


@dataclass(frozen=True, slots=True)
class RankingResolvedInputs:
    opportunity: Opportunity
    snapshot: PersistedRevisionSnapshot
    eligibility: EligibilityDecision
    assessment: OpportunityProfileAssessment
    opportunity_content_digest: str
    include_fake_assessments: bool

    @property
    def theme_by_key(self) -> dict[str, SearchTheme]:
        return {
            theme.theme_key: theme
            for theme in self.snapshot.themes
            if theme.is_active
        }
