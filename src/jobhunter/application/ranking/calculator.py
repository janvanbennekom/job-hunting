"""Pure deterministic ranking_v1 calculator."""

from __future__ import annotations

from dataclasses import dataclass

from jobhunter.application.ranking import ranking_config_v1 as config
from jobhunter.application.ranking.digests import compute_ranking_input_digest
from jobhunter.application.ranking.inputs import RankingResolvedInputs
from jobhunter.domain.assessment_enums import (
    AlignmentLevel,
    OverallRelevance,
    SourceDataSufficiency,
)
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.ranking_enums import RANKING_METHOD_VERSION
from jobhunter.domain.ranking_enums import (
    ExclusionReason,
    FactorEffect,
    PriorityBand,
    RankingStatus,
    UnrankedReason,
)
from jobhunter.domain.ranking_factor import RankingFactor
from jobhunter.domain.serialization import value_to_enum


@dataclass(slots=True)
class RankingCalculation:
    status: RankingStatus
    priority_band: PriorityBand | None
    internal_sort_score: int | None
    factors: list[RankingFactor]
    warnings: list[str]
    exclusion_reason: str | None
    unranked_reason: str | None
    input_digest: str | None
    eligibility_decision_id: str | None
    profile_assessment_id: str | None


class OpportunityRankingCalculator:
    def calculate(self, resolved: RankingResolvedInputs) -> RankingCalculation:
        opp = resolved.opportunity
        eligibility = resolved.eligibility
        assessment = resolved.assessment
        revision_id = resolved.snapshot.revision.id

        if opp.lifecycle_status is LifecycleStatus.CLOSED:
            reason = ExclusionReason.LIFECYCLE_CLOSED.value
        elif opp.lifecycle_status is LifecycleStatus.EXPIRED:
            reason = ExclusionReason.LIFECYCLE_EXPIRED.value
        else:
            reason = None

        if reason is not None:
            return RankingCalculation(
                status=RankingStatus.EXCLUDED,
                priority_band=None,
                internal_sort_score=None,
                factors=[],
                warnings=[],
                exclusion_reason=reason,
                unranked_reason=None,
                input_digest=None,
                eligibility_decision_id=eligibility.id,
                profile_assessment_id=assessment.id,
            )

        if eligibility.status is EligibilityStatus.INELIGIBLE:
            return RankingCalculation(
                status=RankingStatus.EXCLUDED,
                priority_band=None,
                internal_sort_score=None,
                factors=[
                    RankingFactor(
                        code="ELIGIBILITY_INELIGIBLE",
                        effect=FactorEffect.INFORMATIONAL,
                        summary="Opportunity is ineligible under current strategy.",
                    )
                ],
                warnings=[],
                exclusion_reason=ExclusionReason.INELIGIBLE.value,
                unranked_reason=None,
                input_digest=None,
                eligibility_decision_id=eligibility.id,
                profile_assessment_id=assessment.id,
            )

        if eligibility.search_strategy_revision_id != revision_id:
            return self._unranked(
                UnrankedReason.ELIGIBILITY_REVISION_MISMATCH,
                eligibility.id,
                assessment.id,
            )

        if assessment.search_strategy_revision_id != revision_id:
            return self._unranked(
                UnrankedReason.ASSESSMENT_REVISION_MISMATCH,
                eligibility.id,
                assessment.id,
            )

        if not assessment.is_successful:
            return self._unranked(
                UnrankedReason.FAILED_ASSESSMENT,
                eligibility.id,
                assessment.id,
            )

        if assessment.model_provider == "fake" and not resolved.include_fake_assessments:
            return self._unranked(
                UnrankedReason.NON_PRODUCTION_ASSESSMENT,
                eligibility.id,
                assessment.id,
                warnings=["NON_PRODUCTION_ASSESSMENT"],
            )

        result = assessment.result or {}
        factors: list[RankingFactor] = []
        warnings: list[str] = []
        score = 0

        overall_raw = result.get("overall_relevance", OverallRelevance.UNKNOWN.value)
        try:
            overall = OverallRelevance(str(overall_raw))
        except ValueError:
            overall = OverallRelevance.UNKNOWN
        overall_pts = config.OVERALL_RELEVANCE_POINTS[overall]
        score += overall_pts
        factors.append(
            RankingFactor(
                code="OVERALL_RELEVANCE",
                effect=_effect_for_points(overall_pts),
                summary=f"Overall relevance assessed as {overall.value}.",
                contribution=overall_pts,
            )
        )

        service_pts = _best_service_alignment_points(result)
        score += service_pts
        if service_pts:
            factors.append(
                RankingFactor(
                    code="SERVICE_ALIGNMENT",
                    effect=_effect_for_points(service_pts),
                    summary="Strongest professional-service alignment from assessment.",
                    contribution=service_pts,
                )
            )

        theme_pts, theme_factors = _theme_contribution(
            result, resolved.theme_by_key
        )
        score += theme_pts
        factors.extend(theme_factors)

        elig_pts = config.ELIGIBILITY_STATUS_POINTS[eligibility.status]
        score += elig_pts
        factors.append(
            RankingFactor(
                code="ELIGIBILITY_STATUS",
                effect=_effect_for_points(elig_pts),
                summary=f"Eligibility status is {eligibility.status.value}.",
                contribution=elig_pts,
            )
        )

        suff_raw = result.get(
            "source_data_sufficiency",
            SourceDataSufficiency.LIST_SUMMARY_ONLY.value,
        )
        try:
            sufficiency = SourceDataSufficiency(str(suff_raw))
        except ValueError:
            sufficiency = SourceDataSufficiency.LIST_SUMMARY_ONLY
        suff_pts = config.SOURCE_SUFFICIENCY_POINTS[sufficiency]
        score += suff_pts
        if sufficiency is SourceDataSufficiency.LIST_SUMMARY_ONLY:
            warnings.append("LIST_SUMMARY_ONLY")
            factors.append(
                RankingFactor(
                    code="SOURCE_DATA_LIST_SUMMARY_ONLY",
                    effect=FactorEffect.INFORMATIONAL,
                    summary=(
                        "Ranking uses limited list-derived opportunity text; "
                        "evidence certainty is reduced."
                    ),
                    contribution=suff_pts,
                )
            )
        elif suff_pts:
            factors.append(
                RankingFactor(
                    code="SOURCE_DATA_SUFFICIENCY",
                    effect=_effect_for_points(suff_pts),
                    summary=f"Source data sufficiency: {sufficiency.value}.",
                    contribution=suff_pts,
                )
            )

        interpreted_pts = _interpreted_eligibility_points(result, factors)

        score += interpreted_pts

        for note in result.get("preference_notes") or []:
            if isinstance(note, dict) and note.get("note"):
                factors.append(
                    RankingFactor(
                        code="PREFERENCE_NOTE",
                        effect=FactorEffect.INFORMATIONAL,
                        summary=str(note.get("note")),
                    )
                )

        if resolved.include_fake_assessments and assessment.model_provider == "fake":
            warnings.append("DEVELOPMENT_FAKE_ASSESSMENT")

        band = _resolve_priority_band(score, eligibility.status)

        input_digest = compute_ranking_input_digest(
            opportunity_content_digest=resolved.opportunity_content_digest,
            eligibility_decision_id=eligibility.id,
            profile_assessment_id=assessment.id,
            search_strategy_revision_id=revision_id,
            ranking_method_version=RANKING_METHOD_VERSION,
            ranking_config_hash=config.compute_ranking_config_hash(),
        )

        return RankingCalculation(
            status=RankingStatus.RANKED,
            priority_band=band,
            internal_sort_score=score,
            factors=factors,
            warnings=warnings,
            exclusion_reason=None,
            unranked_reason=None,
            input_digest=input_digest,
            eligibility_decision_id=eligibility.id,
            profile_assessment_id=assessment.id,
        )

    @staticmethod
    def _unranked(
        reason: UnrankedReason,
        eligibility_id: str | None,
        assessment_id: str | None,
        *,
        warnings: list[str] | None = None,
    ) -> RankingCalculation:
        return RankingCalculation(
            status=RankingStatus.UNRANKED,
            priority_band=None,
            internal_sort_score=None,
            factors=[],
            warnings=list(warnings or []),
            exclusion_reason=None,
            unranked_reason=reason.value,
            input_digest=None,
            eligibility_decision_id=eligibility_id,
            profile_assessment_id=assessment_id,
        )


def _effect_for_points(points: int) -> FactorEffect:
    if points > 0:
        return FactorEffect.INCREASED
    if points < 0:
        return FactorEffect.DECREASED
    return FactorEffect.NEUTRAL


def _best_service_alignment_points(result: dict) -> int:
    best = 0
    for item in result.get("service_alignments") or []:
        if not isinstance(item, dict):
            continue
        try:
            level = AlignmentLevel(str(item.get("alignment", "NONE")))
        except ValueError:
            continue
        best = max(best, config.SERVICE_ALIGNMENT_POINTS[level])
    return best


def _theme_contribution(
    result: dict,
    theme_by_key: dict,
) -> tuple[int, list[RankingFactor]]:
    total = 0
    factors: list[RankingFactor] = []
    for item in result.get("theme_alignments") or []:
        if not isinstance(item, dict):
            continue
        theme_key = str(item.get("theme_key", ""))
        theme = theme_by_key.get(theme_key)
        if theme is None:
            continue
        try:
            alignment = AlignmentLevel(str(item.get("alignment", "NONE")))
        except ValueError:
            continue
        align_pts = config.THEME_ALIGNMENT_POINTS[alignment]
        mult = config.THEME_STRENGTH_MULTIPLIER[theme.strength]
        contribution = align_pts * mult
        total += contribution
        factors.append(
            RankingFactor(
                code=f"THEME_{theme_key}",
                effect=_effect_for_points(contribution),
                summary=(
                    f"Theme {theme.label!r} alignment {alignment.value} "
                    f"with strategy strength {theme.strength.value}."
                ),
                contribution=contribution,
            )
        )
    if total > config.THEME_CONTRIBUTION_CAP:
        excess = total - config.THEME_CONTRIBUTION_CAP
        total = config.THEME_CONTRIBUTION_CAP
        factors.append(
            RankingFactor(
                code="THEME_CONTRIBUTION_CAP",
                effect=FactorEffect.DECREASED,
                summary="Theme contributions capped for ranking_v1.",
                contribution=-excess,
            )
        )
    return total, factors


def _interpreted_eligibility_points(
    result: dict,
    factors: list[RankingFactor],
) -> int:
    total = 0
    for item in result.get("interpreted_eligibility") or []:
        if not isinstance(item, dict):
            continue
        try:
            concern = value_to_enum(
                AlignmentLevel, item.get("concern_level", "UNKNOWN")
            )
        except (ValueError, KeyError):
            concern = AlignmentLevel.UNKNOWN
        pts = config.INTERPRETED_CONCERN_POINTS[concern]
        if pts:
            total += pts
            factors.append(
                RankingFactor(
                    code="INTERPRETED_ELIGIBILITY",
                    effect=FactorEffect.DECREASED,
                    summary=str(item.get("rationale") or "Interpreted eligibility concern."),
                    contribution=pts,
                )
            )
    return max(total, config.INTERPRETED_CONCERN_CAP)


def _resolve_priority_band(
    score: int,
    eligibility_status: EligibilityStatus,
) -> PriorityBand:
    if eligibility_status in config.ELIGIBILITY_REVIEW_BAND:
        return PriorityBand.REVIEW
    if score >= config.BAND_HIGH_MIN_SCORE:
        return PriorityBand.HIGH
    if score >= config.BAND_MEDIUM_MIN_SCORE:
        return PriorityBand.MEDIUM
    return PriorityBand.LOW
