"""Unit tests for ranking_v1 calculator."""

from __future__ import annotations

from datetime import date, datetime, timezone

from jobhunter.application.ranking.calculator import OpportunityRankingCalculator
from jobhunter.application.ranking.inputs import RankingResolvedInputs
from jobhunter.application.ranking import ranking_config_v1 as config
from jobhunter.domain.assessment_enums import (
    AssessmentStatus,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.eligibility_decision import EligibilityDecision
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus, OpportunityType
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.ranking_enums import PriorityBand, RankingStatus
from jobhunter.domain.search_strategy_revision import SearchStrategyRevision
from jobhunter.domain.search_theme import SearchTheme
from jobhunter.domain.strategy_enums import (
    PreferenceStrength,
    RevisionChangeSource,
    RevisionStatus,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    PersistedRevisionSnapshot,
)


def _revision(rev_id: str = "rev-1") -> PersistedRevisionSnapshot:
    revision = SearchStrategyRevision(
        id=rev_id,
        search_strategy_id="strat-1",
        revision_number=1,
        status=RevisionStatus.ACTIVE,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        change_summary="t",
        change_source=RevisionChangeSource.INITIAL_SEED,
        content_hash="a" * 64,
    )
    themes = [
        SearchTheme(
            id="theme-1",
            revision_id=rev_id,
            theme_key="lis_implementation",
            label="LIS",
            strength=PreferenceStrength.STRONGLY_PREFERRED,
        )
    ]
    return PersistedRevisionSnapshot(
        revision=revision, themes=themes, criteria=[], exclusions=[]
    )


def _assessment(
    result: dict,
    *,
    provider: str = "openai",
    rev_id: str = "rev-1",
) -> OpportunityProfileAssessment:
    return OpportunityProfileAssessment(
        opportunity_id="opp-1",
        search_strategy_revision_id=rev_id,
        assessed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        status=AssessmentStatus.SUCCEEDED,
        input_digest="b" * 64,
        opportunity_content_digest="c" * 64,
        profile_evidence_digest="d" * 64,
        prompt_schema_version="profile_assessment_v1",
        model_provider=provider,
        model_name="test-model",
        eligibility_decision_id="dec-1",
        result=result,
    )


def _resolved(
    result: dict,
    *,
    eligibility: EligibilityStatus = EligibilityStatus.ELIGIBLE,
    provider: str = "openai",
    include_fake: bool = False,
) -> RankingResolvedInputs:
    return RankingResolvedInputs(
        opportunity=Opportunity(
            id="opp-1",
            title="LIS consultant",
            deadline=date(2026, 12, 31),
            publication_date=date(2026, 1, 1),
            lifecycle_status=LifecycleStatus.NEW,
        ),
        snapshot=_revision(),
        eligibility=EligibilityDecision(
            id="dec-1",
            opportunity_id="opp-1",
            search_strategy_revision_id="rev-1",
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=eligibility,
        ),
        assessment=_assessment(result, provider=provider),
        opportunity_content_digest="e" * 64,
        include_fake_assessments=include_fake,
    )


def test_list_summary_only_can_still_be_high() -> None:
    calc = OpportunityRankingCalculator().calculate(
        _resolved(
            {
                "overall_relevance": OverallRelevance.STRONG_FIT.value,
                "source_data_sufficiency": SourceDataSufficiency.LIST_SUMMARY_ONLY.value,
                "service_alignments": [],
                "theme_alignments": [],
            }
        )
    )
    assert calc.status is RankingStatus.RANKED
    assert calc.priority_band is PriorityBand.HIGH
    assert "LIST_SUMMARY_ONLY" in calc.warnings


def test_review_required_forces_review_band() -> None:
    calc = OpportunityRankingCalculator().calculate(
        _resolved(
            {
                "overall_relevance": OverallRelevance.STRONG_FIT.value,
                "source_data_sufficiency": SourceDataSufficiency.ADEQUATE.value,
            },
            eligibility=EligibilityStatus.REVIEW_REQUIRED,
        )
    )
    assert calc.priority_band is PriorityBand.REVIEW


def test_fake_excluded_without_dev_flag() -> None:
    calc = OpportunityRankingCalculator().calculate(
        _resolved(
            {"overall_relevance": OverallRelevance.STRONG_FIT.value},
            provider="fake",
            include_fake=False,
        )
    )
    assert calc.status is RankingStatus.UNRANKED


def test_fake_allowed_with_dev_flag() -> None:
    calc = OpportunityRankingCalculator().calculate(
        _resolved(
            {"overall_relevance": OverallRelevance.MODERATE_FIT.value},
            provider="fake",
            include_fake=True,
        )
    )
    assert calc.status is RankingStatus.RANKED
    assert "DEVELOPMENT_FAKE_ASSESSMENT" in calc.warnings


def test_ineligible_excluded() -> None:
    calc = OpportunityRankingCalculator().calculate(
        _resolved(
            {"overall_relevance": OverallRelevance.STRONG_FIT.value},
            eligibility=EligibilityStatus.INELIGIBLE,
        )
    )
    assert calc.status is RankingStatus.EXCLUDED


def test_theme_alignment_contribution() -> None:
    calc = OpportunityRankingCalculator().calculate(
        _resolved(
            {
                "overall_relevance": OverallRelevance.MODERATE_FIT.value,
                "source_data_sufficiency": SourceDataSufficiency.ADEQUATE.value,
                "theme_alignments": [
                    {
                        "theme_key": "lis_implementation",
                        "alignment": "STRONG",
                        "basis": "INFERENCE",
                        "rationale": "x",
                    }
                ],
            }
        )
    )
    assert any(f.code.startswith("THEME_") for f in calc.factors)


def test_config_hash_stable() -> None:
    assert config.compute_ranking_config_hash() == config.compute_ranking_config_hash()
