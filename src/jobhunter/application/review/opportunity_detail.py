"""Opportunity detail assembly for Phase 10."""

from __future__ import annotations

from sqlalchemy.orm import Session

from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
from jobhunter.application.review.dtos import (
    AssessmentSectionView,
    OpportunityQueueFilters,
    EligibilityRuleView,
    EligibilitySectionView,
    HumanReviewSectionView,
    OpportunityDetailView,
    OpportunityFactsSectionView,
    ProvenanceObservationView,
    RankingFactorView,
    RankingSectionView,
)
from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
from jobhunter.application.review.opportunity_reads import OpportunityPipelineReader
from jobhunter.application.review.profile_labels import ProfileLabelResolver
from jobhunter.application.review.source_links import (
    build_source_link_views,
    pick_primary_source_link,
)
from jobhunter.domain.assessment_enums import AssessmentStatus
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import RankingStatus
from jobhunter.infrastructure.persistence.eligibility_repositories import (
    EligibilityDecisionRepository,
    EligibilityRuleResultRepository,
)
from jobhunter.infrastructure.persistence.opportunity_processing_repositories import (
    OpportunityObservationRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    JobSourceRepository,
    OpportunityRepository,
    OpportunitySourceRepository,
    RawOpportunityRepository,
)
from jobhunter.infrastructure.persistence.review_repositories import (
    OpportunityReviewRecordRepository,
)


def _load_pursuit_view(session: Session, opportunity_id: str):
    from jobhunter.application.pursuit.service import PursuitTrackingService

    return PursuitTrackingService(session).get_current(opportunity_id)


class OpportunityDetailService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._opportunities = OpportunityRepository(session)
        self._opp_sources = OpportunitySourceRepository(session)
        self._job_sources = JobSourceRepository(session)
        self._raw = RawOpportunityRepository(session)
        self._observations = OpportunityObservationRepository(session)
        self._eligibility = EligibilityDecisionRepository(session)
        self._rule_results = EligibilityRuleResultRepository(session)
        self._reviews = OpportunityReviewRecordRepository(session)
        self._strategy = ActiveSearchStrategyResolver(session)
        self._pipeline = OpportunityPipelineReader(session)
        self._labels = ProfileLabelResolver(session)
        self._queue = OpportunityReviewQueryService(session)

    def get_detail(
        self, opportunity_id: str, *, allow_fake: bool = False
    ) -> OpportunityDetailView | None:
        opp = self._opportunities.get_by_id(opportunity_id)
        if opp is None:
            return None

        ctx = self._strategy.resolve()
        revision_id = ctx.revision_id
        pipeline = self._pipeline.load(opp, revision_id, allow_fake=allow_fake)

        links = self._opp_sources.list_for_opportunity(opp.id)
        source_views = build_source_link_views(links, self._job_sources)
        primary = pick_primary_source_link(links, self._job_sources)

        observations: list[ProvenanceObservationView] = []
        for obs in self._observations.list_for_opportunity(opp.id):
            raw = self._raw.get_by_id(obs.raw_opportunity_id)
            observations.append(
                ProvenanceObservationView(
                    observed_at=obs.observed_at,
                    lifecycle_status=obs.lifecycle_status,
                    raw_opportunity_id=obs.raw_opportunity_id,
                    raw_title=raw.raw_title if raw else None,
                    retrieved_at=raw.retrieved_at if raw else None,
                )
            )

        facts = OpportunityFactsSectionView(
            opportunity_id=opp.id,
            title=opp.title,
            organisation=opp.organisation,
            location=opp.location,
            description=opp.description,
            publication_date=opp.publication_date,
            deadline=opp.deadline,
            expected_start_date=opp.expected_start_date,
            opportunity_type=opp.opportunity_type.value,
            lifecycle_status=opp.lifecycle_status,
            eligibility_status=opp.eligibility_status,
            source_status=opp.source_status,
            primary_external_url=primary.external_url if primary else None,
            source_links=source_views,
            observations=observations,
        )

        eligibility_section = self._build_eligibility(opp.id, revision_id)
        assessment_section = self._build_assessment(pipeline, allow_fake)
        ranking_section = self._build_ranking(
            opp, revision_id, allow_fake, pipeline.display_ranking
        )
        human_section = self._build_human_review(opp.id)

        result_for_labels = assessment_section.result
        label_map = self._labels.build_map_for_result(result_for_labels)

        return OpportunityDetailView(
            facts=facts,
            eligibility=eligibility_section,
            assessment=assessment_section,
            ranking=ranking_section,
            human_review=human_section,
            pursuit=_load_pursuit_view(self._session, opp.id),
            profile_labels=label_map,
        )

    def _build_eligibility(
        self, opportunity_id: str, revision_id: str
    ) -> EligibilitySectionView | None:
        decision = self._eligibility.get_latest_for_opportunity_and_revision(
            opportunity_id, revision_id
        )
        if decision is None:
            return None
        rules = self._rule_results.list_for_decision(decision.id)
        return EligibilitySectionView(
            status=decision.status,
            decision_id=decision.id,
            evaluated_at=decision.evaluated_at,
            search_strategy_revision_id=decision.search_strategy_revision_id,
            rule_results=[
                EligibilityRuleView(
                    rule_kind=rule.rule_kind.value,
                    rule_code=rule.rule_code,
                    outcome=rule.outcome.value,
                    suggests_review=rule.suggests_review,
                    summary=rule.summary,
                    evidence=rule.evidence,
                )
                for rule in rules
            ],
        )

    def _build_assessment(self, pipeline, allow_fake: bool) -> AssessmentSectionView:
        assessment = pipeline.display_assessment
        if assessment is None:
            explanation = None
            if pipeline.assessment_state.value == "FAKE_ONLY":
                explanation = (
                    "No production assessment is stored. Only development/fake "
                    "assessments exist for this opportunity."
                )
            elif pipeline.latest_assessment and pipeline.latest_assessment.status in (
                AssessmentStatus.FAILED_VALIDATION,
                AssessmentStatus.FAILED_PROVIDER,
            ):
                explanation = "The latest assessment attempt failed."
            else:
                explanation = "No successful profile assessment for the active strategy revision."
            return AssessmentSectionView(
                present=False,
                is_fake=False,
                assessment_id=None,
                status=None,
                assessed_at=None,
                model_provider=None,
                model_name=None,
                prompt_schema_version=None,
                validation_warnings=[],
                provider_error=pipeline.latest_assessment.provider_error
                if pipeline.latest_assessment
                else None,
                result=None,
                explanation=explanation,
            )

        is_fake = assessment.model_provider == "fake"
        return AssessmentSectionView(
            present=True,
            is_fake=is_fake,
            assessment_id=assessment.id,
            status=assessment.status.value,
            assessed_at=assessment.assessed_at,
            model_provider=assessment.model_provider,
            model_name=assessment.model_name,
            prompt_schema_version=assessment.prompt_schema_version,
            validation_warnings=list(assessment.validation_warnings),
            provider_error=assessment.provider_error,
            result=assessment.result,
            explanation=(
                "AI-generated inference grounded in opportunity text and selected "
                "professional profile evidence."
                + (" (Development/fake model.)" if is_fake and allow_fake else "")
            ),
        )

    def _build_ranking(
        self, opp, revision_id: str, allow_fake: bool, ranking
    ) -> RankingSectionView:
        dynamic_rank = None
        for item in self._queue.list_queue(
            OpportunityQueueFilters(allow_fake=allow_fake)
        ):
            if item.opportunity_id == opp.id:
                dynamic_rank = item.dynamic_rank
                break

        if ranking is None:
            return RankingSectionView(
                dynamic_rank=None,
                status=None,
                priority_band=None,
                factors=[],
                warnings=[],
                ranking_method_version=None,
                ranking_config_hash=None,
                eligibility_decision_id=None,
                profile_assessment_id=None,
                ranking_id=None,
                unranked_reason=None,
                exclusion_reason=None,
                explanation="No ranking record for the active search strategy revision.",
            )

        explanation = None
        if ranking.status is not RankingStatus.RANKED:
            reason = ranking.unranked_reason or ranking.exclusion_reason
            explanation = f"Not ranked ({reason or 'see status'})."
        if opp.lifecycle_status in (LifecycleStatus.CLOSED, LifecycleStatus.EXPIRED):
            explanation = (
                f"Lifecycle is {opp.lifecycle_status.value}; ranking is not actionable."
            )
        if opp.eligibility_status is EligibilityStatus.INELIGIBLE:
            explanation = "Opportunity is ineligible under deterministic rules."

        factors = [
            RankingFactorView(
                code=factor.code,
                effect=factor.effect.value,
                summary=factor.summary,
                contribution=factor.contribution,
            )
            for factor in ranking.factors
        ]

        return RankingSectionView(
            dynamic_rank=dynamic_rank,
            status=ranking.status,
            priority_band=ranking.priority_band,
            factors=factors,
            warnings=list(ranking.warnings),
            ranking_method_version=ranking.ranking_method_version,
            ranking_config_hash=ranking.ranking_config_hash,
            eligibility_decision_id=ranking.eligibility_decision_id,
            profile_assessment_id=ranking.profile_assessment_id,
            ranking_id=ranking.id,
            unranked_reason=ranking.unranked_reason,
            exclusion_reason=ranking.exclusion_reason,
            explanation=explanation,
        )

    def _build_human_review(self, opportunity_id: str) -> HumanReviewSectionView:
        history_rows = self._reviews.list_for_opportunity(opportunity_id)
        latest = history_rows[0] if history_rows else None
        history = [
            (row.disposition, row.recorded_at, row.notes) for row in history_rows
        ]
        return HumanReviewSectionView(
            current_disposition=latest.disposition if latest else None,
            current_notes=latest.notes if latest else None,
            current_recorded_at=latest.recorded_at if latest else None,
            history=history,
        )
