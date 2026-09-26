"""Orchestrate opportunity ranking (Phase 9)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.application.ranking import ranking_config_v1 as config
from jobhunter.application.ranking.calculator import (
    OpportunityRankingCalculator,
    RankingCalculation,
)
from jobhunter.application.profile_assessment.digests import (
    compute_opportunity_content_digest,
)
from jobhunter.application.ranking.digests import (
    compute_ranking_state_digest,
    default_ranking_method_version,
)
from jobhunter.application.ranking.ordering import RankedOpportunityView, sort_ranked_views
from jobhunter.application.ranking.resolver import RankingInputResolver, RankingResolveFailure
from jobhunter.domain.opportunity_ranking import OpportunityRanking
from jobhunter.domain.ranking_enums import RANKING_METHOD_VERSION, RankingStatus
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.ranking_repositories import (
    OpportunityRankingRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    StrategyRevisionSnapshotRepository,
)


@dataclass(slots=True)
class RankingOutcome:
    ranking: OpportunityRanking
    reused: bool
    computed: RankingCalculation | None = None


class OpportunityRankingService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._rankings = OpportunityRankingRepository(session)
        self._strategies = SearchStrategyRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)
        self._resolver = RankingInputResolver(session)
        self._calculator = OpportunityRankingCalculator()

    def resolve_active_snapshot(self, owner_key: str = PRIMARY_PROFILE_KEY):
        strategy = self._strategies.get_by_owner_key(owner_key)
        if strategy is None or strategy.current_revision_id is None:
            raise RuntimeError(
                f"No active search strategy revision for owner {owner_key!r}"
            )
        snapshot = self._snapshots.load_snapshot(strategy.current_revision_id)
        if snapshot is None:
            raise RuntimeError(
                f"Search strategy revision {strategy.current_revision_id} not found"
            )
        return snapshot

    def rank_opportunity(
        self,
        opportunity_id: str,
        *,
        owner_key: str = PRIMARY_PROFILE_KEY,
        include_fake_assessments: bool = False,
        force: bool = False,
        dry_run: bool = False,
        ranked_at: datetime | None = None,
    ) -> RankingOutcome:
        when = ranked_at or datetime.now(timezone.utc)
        snapshot = self.resolve_active_snapshot(owner_key)
        resolved = self._resolver.resolve(
            opportunity_id,
            snapshot,
            include_fake_assessments=include_fake_assessments,
        )

        if isinstance(resolved, RankingResolveFailure):
            calc = self._failure_calculation(resolved, snapshot.revision.id, when)
            if dry_run:
                return RankingOutcome(
                    self._entity_from_calculation(
                        opportunity_id, snapshot.revision.id, when, calc
                    ),
                    False,
                    calc,
                )
            entity = self._persist_calculation(
                opportunity_id, snapshot.revision.id, when, calc
            )
            return RankingOutcome(entity, False, calc)

        computed = self._calculator.calculate(resolved)
        if computed.input_digest and not force:
            existing = self._rankings.find_reusable_by_digest(
                opportunity_id, computed.input_digest
            )
            if existing is not None:
                return RankingOutcome(existing, True, computed)

        if dry_run:
            return RankingOutcome(
                self._entity_from_calculation(
                    opportunity_id, snapshot.revision.id, when, computed
                ),
                False,
                computed,
            )

        entity = self._persist_calculation(
            opportunity_id, snapshot.revision.id, when, computed
        )
        return RankingOutcome(entity, False, computed)

    def rank_opportunity_ids(
        self,
        opportunity_ids: list[str],
        **kwargs,
    ) -> list[RankingOutcome]:
        return [self.rank_opportunity(opp_id, **kwargs) for opp_id in opportunity_ids]

    def current_ranked_views(
        self,
        opportunity_ids: list[str],
        *,
        owner_key: str = PRIMARY_PROFILE_KEY,
        include_fake_assessments: bool = False,
        force_recompute: bool = False,
    ) -> list[RankedOpportunityView]:
        outcomes = self.rank_opportunity_ids(
            opportunity_ids,
            owner_key=owner_key,
            include_fake_assessments=include_fake_assessments,
            force=force_recompute,
            dry_run=False,
        )
        views: list[RankedOpportunityView] = []
        for outcome in outcomes:
            opp = self._opportunities.get_by_id(outcome.ranking.opportunity_id)
            if opp is None:
                continue
            if outcome.ranking.status is RankingStatus.RANKED:
                views.append(RankedOpportunityView(opportunity=opp, ranking=outcome.ranking))
        return sort_ranked_views(views)

    def _failure_calculation(
        self,
        failure: RankingResolveFailure,
        revision_id: str,
        when: datetime,
    ) -> RankingCalculation:
        from jobhunter.application.ranking.calculator import RankingCalculation

        return RankingCalculation(
            status=RankingStatus.UNRANKED,
            priority_band=None,
            internal_sort_score=None,
            factors=[],
            warnings=[],
            exclusion_reason=None,
            unranked_reason=failure.reason.value,
            input_digest=None,
            eligibility_decision_id=(
                failure.eligibility.id if failure.eligibility else None
            ),
            profile_assessment_id=(
                failure.assessment.id if failure.assessment else None
            ),
        )

    def _entity_from_calculation(
        self,
        opportunity_id: str,
        revision_id: str,
        when: datetime,
        calc: RankingCalculation,
    ) -> OpportunityRanking:
        return OpportunityRanking(
            opportunity_id=opportunity_id,
            search_strategy_revision_id=revision_id,
            eligibility_decision_id=calc.eligibility_decision_id,
            profile_assessment_id=calc.profile_assessment_id,
            ranked_at=when,
            status=calc.status,
            priority_band=calc.priority_band,
            input_digest=calc.input_digest or "",
            ranking_method_version=default_ranking_method_version(),
            ranking_config_hash=config.compute_ranking_config_hash(),
            internal_sort_score=calc.internal_sort_score,
            factors=calc.factors,
            warnings=calc.warnings,
            exclusion_reason=calc.exclusion_reason,
            unranked_reason=calc.unranked_reason,
        )

    def _persist_calculation(
        self,
        opportunity_id: str,
        revision_id: str,
        when: datetime,
        calc: RankingCalculation,
    ) -> OpportunityRanking:
        digest = calc.input_digest or self._state_digest(
            opportunity_id, revision_id, calc
        )
        existing = self._rankings.find_reusable_by_digest(opportunity_id, digest)
        if existing is not None:
            return existing
        entity = OpportunityRanking(
            opportunity_id=opportunity_id,
            search_strategy_revision_id=revision_id,
            eligibility_decision_id=calc.eligibility_decision_id,
            profile_assessment_id=calc.profile_assessment_id,
            ranked_at=when,
            status=calc.status,
            priority_band=calc.priority_band,
            input_digest=digest,
            ranking_method_version=RANKING_METHOD_VERSION,
            ranking_config_hash=config.compute_ranking_config_hash(),
            internal_sort_score=calc.internal_sort_score,
            factors=calc.factors,
            warnings=calc.warnings,
            exclusion_reason=calc.exclusion_reason,
            unranked_reason=calc.unranked_reason,
        )
        return self._rankings.save(entity)

    def _state_digest(
        self,
        opportunity_id: str,
        revision_id: str,
        calc: RankingCalculation,
    ) -> str:
        opportunity = self._opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity {opportunity_id} not found")
        reason = calc.unranked_reason or calc.exclusion_reason
        return compute_ranking_state_digest(
            opportunity_content_digest=compute_opportunity_content_digest(opportunity),
            search_strategy_revision_id=revision_id,
            ranking_method_version=RANKING_METHOD_VERSION,
            ranking_config_hash=config.compute_ranking_config_hash(),
            status=calc.status.value,
            eligibility_decision_id=calc.eligibility_decision_id,
            profile_assessment_id=calc.profile_assessment_id,
            reason_code=reason,
        )
