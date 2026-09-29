"""Read models for Phase 10 dashboard (not domain entities)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jobhunter.application.pursuit.dtos import PursuitCurrentView
    from jobhunter.application.review.assessment_presentation import (
        AssessmentOperatorPresentation,
    )

from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.domain.review_enums import ReviewDisposition


class AssessmentDisplayState(StrEnum):
    NONE = "NONE"
    PRODUCTION = "PRODUCTION"
    FAKE_ONLY = "FAKE_ONLY"
    FAKE_DEV = "FAKE_DEV"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class OpportunityQueueFilters:
    allow_fake: bool = False
    include_ineligible: bool = False
    include_non_actionable_lifecycle: bool = False
    ranking_band: PriorityBand | None = None
    lifecycle: LifecycleStatus | None = None
    source_id: str | None = None
    eligibility: EligibilityStatus | None = None
    assessment_state: AssessmentDisplayState | None = None
    location_contains: str | None = None
    review_disposition: ReviewDisposition | None = None


@dataclass(frozen=True, slots=True)
class SourceLinkView:
    source_id: str
    source_name: str
    source_url: str | None
    original_url: str | None
    source_reference: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None

    @property
    def external_url(self) -> str | None:
        """Primary listing URL on the source site (not external application URL)."""
        if self.source_url:
            return self.source_url
        return self.original_url

    @property
    def application_url(self) -> str | None:
        if self.original_url and self.original_url != self.source_url:
            return self.original_url
        return None


@dataclass(frozen=True, slots=True)
class OpportunityQueueItem:
    opportunity_id: str
    title: str
    organisation: str | None
    location: str | None
    deadline: date | None
    lifecycle_status: LifecycleStatus
    eligibility_status: EligibilityStatus
    source_id: str | None
    source_name: str | None
    external_url: str | None
    dynamic_rank: int | None
    ranking_status: RankingStatus | None
    priority_band: PriorityBand | None
    overall_relevance: str | None
    source_data_sufficiency: str | None
    assessment_state: AssessmentDisplayState
    unranked_reason: str | None
    exclusion_reason: str | None
    last_seen_at: datetime | None
    last_processed_at: datetime | None
    review_disposition: ReviewDisposition | None
    ranking_unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class RankingFactorView:
    code: str
    effect: str
    summary: str
    contribution: int | None = None


@dataclass(frozen=True, slots=True)
class RankingSectionView:
    dynamic_rank: int | None
    status: RankingStatus | None
    priority_band: PriorityBand | None
    factors: list[RankingFactorView]
    warnings: list[str]
    ranking_method_version: str | None
    ranking_config_hash: str | None
    eligibility_decision_id: str | None
    profile_assessment_id: str | None
    ranking_id: str | None
    unranked_reason: str | None
    exclusion_reason: str | None
    explanation: str | None = None


@dataclass(frozen=True, slots=True)
class EligibilityRuleView:
    rule_kind: str
    rule_code: str
    outcome: str
    suggests_review: bool
    summary: str | None
    evidence: str | None


@dataclass(frozen=True, slots=True)
class EligibilitySectionView:
    status: EligibilityStatus
    decision_id: str | None
    evaluated_at: datetime | None
    search_strategy_revision_id: str
    rule_results: list[EligibilityRuleView]


@dataclass(frozen=True, slots=True)
class AssessmentSectionView:
    present: bool
    is_fake: bool
    assessment_id: str | None
    status: str | None
    assessed_at: datetime | None
    model_provider: str | None
    model_name: str | None
    prompt_schema_version: str | None
    validation_warnings: list[str]
    provider_error: str | None
    result: dict[str, Any] | None
    explanation: str | None = None
    display_state: AssessmentDisplayState = AssessmentDisplayState.NONE
    operator: AssessmentOperatorPresentation | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceObservationView:
    observed_at: datetime
    lifecycle_status: LifecycleStatus
    raw_opportunity_id: str
    raw_title: str | None
    retrieved_at: datetime | None


@dataclass(frozen=True, slots=True)
class OpportunityFactsSectionView:
    opportunity_id: str
    title: str
    organisation: str | None
    location: str | None
    description: str | None
    publication_date: date | None
    deadline: date | None
    expected_start_date: date | None
    opportunity_type: str
    lifecycle_status: LifecycleStatus
    eligibility_status: EligibilityStatus
    source_status: str | None
    primary_external_url: str | None
    application_url: str | None
    organisation_type: str | None
    contract_type_label: str | None
    minimum_experience_years: int | None
    languages: tuple[str, ...]
    sectors: tuple[str, ...]
    expertise: tuple[str, ...]
    consultant_type_label: str | None
    project_reference: str | None
    duration_label: str | None
    content_last_updated: str | None
    source_links: list[SourceLinkView]
    observations: list[ProvenanceObservationView]


@dataclass(frozen=True, slots=True)
class HumanReviewSectionView:
    current_disposition: ReviewDisposition | None
    current_notes: str | None
    current_recorded_at: datetime | None
    history: list[tuple[ReviewDisposition, datetime, str | None]]


@dataclass(frozen=True, slots=True)
class OpportunityDetailView:
    facts: OpportunityFactsSectionView
    eligibility: EligibilitySectionView | None
    assessment: AssessmentSectionView
    ranking: RankingSectionView
    human_review: HumanReviewSectionView
    pursuit: PursuitCurrentView | None = None
    profile_labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScanSummaryView:
    source_id: str
    source_name: str
    scan_id: str | None
    status: str | None
    started_at: datetime | None
    completed_at: datetime | None
    records_retrieved: int | None
    records_processed: int | None
    records_failed: int | None
    error_summary: str | None


@dataclass(frozen=True, slots=True)
class DashboardSummaryView:
    total_opportunities: int
    by_lifecycle: dict[str, int]
    by_eligibility: dict[str, int]
    actionable_count: int
    production_assessed_count: int
    production_ranked_count: int
    by_ranking_band: dict[str, int]
    latest_scan: ScanSummaryView | None
    high_priority_preview: list[OpportunityQueueItem]
