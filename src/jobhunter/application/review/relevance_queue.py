"""Phase 17G-2B — relevance queue views over production assessment data.

Professional relevance (assessment), ranking band/score, and human review
disposition are independent dimensions. This module encodes presentation/query
policy only; it does not change assessments, rankings, or review records.

LOW ranking band is never used as a relevance gate.
"""

from __future__ import annotations

from collections import Counter
from jobhunter.application.review.dtos import AssessmentDisplayState, OpportunityQueueItem
from jobhunter.domain.assessment_enums import OverallRelevance
from jobhunter.domain.relevance_queue_enums import RelevanceQueueView
from jobhunter.domain.review_enums import ReviewDisposition


_PRIMARY_RELEVANCE = frozenset(
    {OverallRelevance.STRONG_FIT, OverallRelevance.MODERATE_FIT}
)
_NEEDS_REVIEW_RELEVANCE = frozenset(
    {
        OverallRelevance.UNKNOWN,
        OverallRelevance.INSUFFICIENT_EVIDENCE,
    }
)
_RELEVANCE_SORT_PRIMARY = {
    OverallRelevance.STRONG_FIT.value: 0,
    OverallRelevance.MODERATE_FIT.value: 1,
}


def parse_overall_relevance(value: str | None) -> OverallRelevance | None:
    if not value:
        return None
    try:
        return OverallRelevance(value)
    except ValueError:
        return None


def segment_for_item(item: OpportunityQueueItem) -> RelevanceQueueView:
    """Map a queue row to exactly one relevance view segment."""
    if item.assessment_state in (
        AssessmentDisplayState.NONE,
        AssessmentDisplayState.FAILED,
    ):
        return RelevanceQueueView.NEEDS_REVIEW

    relevance = parse_overall_relevance(item.overall_relevance)
    if relevance is None:
        return RelevanceQueueView.NEEDS_REVIEW
    if relevance in _PRIMARY_RELEVANCE:
        return RelevanceQueueView.PRIMARY
    if relevance is OverallRelevance.WEAK_FIT:
        return RelevanceQueueView.WEAK
    if relevance is OverallRelevance.OUT_OF_SCOPE:
        return RelevanceQueueView.OUT_OF_SCOPE
    if relevance in _NEEDS_REVIEW_RELEVANCE:
        return RelevanceQueueView.NEEDS_REVIEW
    return RelevanceQueueView.NEEDS_REVIEW


def matches_relevance_queue(
    item: OpportunityQueueItem, view: RelevanceQueueView | None
) -> bool:
    if view is None:
        return True
    return segment_for_item(item) is view


def apply_hide_dismissed(
    items: list[OpportunityQueueItem], hide_dismissed: bool
) -> list[OpportunityQueueItem]:
    if not hide_dismissed:
        return items
    return [
        item
        for item in items
        if item.review_disposition is not ReviewDisposition.DISMISS
    ]


def count_segments(items: list[OpportunityQueueItem]) -> dict[str, int]:
    counts = Counter(segment_for_item(item).value for item in items)
    return {view.value: counts.get(view.value, 0) for view in RelevanceQueueView}


def sort_queue_for_view(
    items: list[OpportunityQueueItem],
    view: RelevanceQueueView | None,
) -> list[OpportunityQueueItem]:
    if view is RelevanceQueueView.PRIMARY:
        return sorted(items, key=_primary_sort_key)
    if view is RelevanceQueueView.OUT_OF_SCOPE:
        return sorted(items, key=_out_of_scope_sort_key)
    if view is RelevanceQueueView.NEEDS_REVIEW:
        return sorted(items, key=_needs_review_sort_key)
    return items


def _primary_sort_key(item: OpportunityQueueItem) -> tuple:
    reviewed = 1 if item.review_disposition is not None else 0
    rel = item.overall_relevance or ""
    rel_order = _RELEVANCE_SORT_PRIMARY.get(rel, 50)
    rank = item.dynamic_rank if item.dynamic_rank is not None else 1_000_000
    return (reviewed, rel_order, rank, str(item.deadline or ""), item.title)


def _out_of_scope_sort_key(item: OpportunityQueueItem) -> tuple:
    rank = item.dynamic_rank if item.dynamic_rank is not None else 1_000_000
    return (rank, item.title)


def _needs_review_sort_key(item: OpportunityQueueItem) -> tuple:
    state_order = {
        AssessmentDisplayState.FAILED: 0,
        AssessmentDisplayState.NONE: 1,
        AssessmentDisplayState.FAKE_ONLY: 2,
        AssessmentDisplayState.PRODUCTION: 3,
        AssessmentDisplayState.FAKE_DEV: 4,
    }
    return (state_order.get(item.assessment_state, 9), item.title)
