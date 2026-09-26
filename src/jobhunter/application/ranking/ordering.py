"""Dynamic ordering of ranked opportunities (no persisted rank_sequence)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus

_BAND_ORDER: dict[PriorityBand, int] = {
    PriorityBand.HIGH: 0,
    PriorityBand.MEDIUM: 1,
    PriorityBand.LOW: 2,
    PriorityBand.REVIEW: 3,
}


@dataclass(frozen=True, slots=True)
class RankedOpportunityView:
    opportunity: Opportunity
    ranking: OpportunityRanking


def sort_ranked_views(views: list[RankedOpportunityView]) -> list[RankedOpportunityView]:
    return sorted(views, key=_sort_key)


def _sort_key(view: RankedOpportunityView) -> tuple:
    ranking = view.ranking
    opp = view.opportunity
    if ranking.status is not RankingStatus.RANKED or ranking.priority_band is None:
        return (99, 0, date.max, date.min, opp.id)
    band = _BAND_ORDER.get(ranking.priority_band, 50)
    score = ranking.internal_sort_score or 0
    deadline = opp.deadline or date.max
    pub_ord = opp.publication_date.toordinal() if opp.publication_date else 0
    return (band, -score, deadline, -pub_ord, opp.id)
