"""Mappers for opportunity ranking persistence."""

from __future__ import annotations

from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.domain.ranking_factor import RankingFactor
from jobhunter.infrastructure.persistence.models import OpportunityRankingRow


def ranking_to_row(entity: OpportunityRanking) -> OpportunityRankingRow:
    return OpportunityRankingRow(
        id=entity.id,
        opportunity_id=entity.opportunity_id,
        search_strategy_revision_id=entity.search_strategy_revision_id,
        eligibility_decision_id=entity.eligibility_decision_id,
        profile_assessment_id=entity.profile_assessment_id,
        ranked_at=entity.ranked_at,
        status=entity.status.value,
        priority_band=(
            entity.priority_band.value if entity.priority_band is not None else None
        ),
        input_digest=entity.input_digest,
        ranking_method_version=entity.ranking_method_version,
        ranking_config_hash=entity.ranking_config_hash,
        internal_sort_score=entity.internal_sort_score,
        factors=[f.to_mapping() for f in entity.factors],
        warnings=list(entity.warnings),
        exclusion_reason=entity.exclusion_reason,
        unranked_reason=entity.unranked_reason,
    )


def ranking_to_domain(row: OpportunityRankingRow) -> OpportunityRanking:
    factors = [
        RankingFactor.from_mapping(item) for item in (row.factors or [])
    ]
    return OpportunityRanking(
        id=row.id,
        opportunity_id=row.opportunity_id,
        search_strategy_revision_id=row.search_strategy_revision_id,
        eligibility_decision_id=row.eligibility_decision_id,
        profile_assessment_id=row.profile_assessment_id,
        ranked_at=row.ranked_at,
        status=RankingStatus(row.status),
        priority_band=(
            PriorityBand(row.priority_band) if row.priority_band is not None else None
        ),
        input_digest=row.input_digest,
        ranking_method_version=row.ranking_method_version,
        ranking_config_hash=row.ranking_config_hash,
        internal_sort_score=row.internal_sort_score,
        factors=factors,
        warnings=[str(w) for w in (row.warnings or [])],
        exclusion_reason=row.exclusion_reason,
        unranked_reason=row.unranked_reason,
    )
