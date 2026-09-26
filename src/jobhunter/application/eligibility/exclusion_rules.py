"""Deterministic evaluation of configured ExclusionCriterion rules."""

from __future__ import annotations

import re

from jobhunter.application.eligibility.opportunity_text import opportunity_text_corpus
from jobhunter.domain.eligibility_enums import EligibilityRuleKind, RuleTriState
from jobhunter.domain.eligibility_rule_result import EligibilityRuleResult
from jobhunter.domain.exclusion_criterion import ExclusionCriterion
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.strategy_enums import ExclusionCode


def _result(
    decision_id: str,
    code: ExclusionCode,
    outcome: RuleTriState,
    *,
    suggests_review: bool = False,
    summary: str | None = None,
    evidence: str | None = None,
) -> EligibilityRuleResult:
    return EligibilityRuleResult(
        decision_id=decision_id,
        rule_kind=EligibilityRuleKind.EXCLUSION,
        rule_code=code.value,
        outcome=outcome,
        suggests_review=suggests_review,
        summary=summary,
        evidence=evidence,
    )


def evaluate_exclusion(
    opportunity: Opportunity,
    exclusion: ExclusionCriterion,
    *,
    decision_id: str,
) -> EligibilityRuleResult:
    if not exclusion.is_active:
        return _result(
            decision_id,
            exclusion.exclusion_code,
            RuleTriState.TRUE,
            summary="Exclusion inactive; skipped",
        )

    corpus = opportunity_text_corpus(opportunity)
    code = exclusion.exclusion_code

    if code is ExclusionCode.JUNIOR_OR_INTERNSHIP:
        strong = [
            r"\binternship programme\b",
            r"\binternship program\b",
            r"\bgraduate internship\b",
            r"\byouth internship\b",
        ]
        review = [
            r"\binternship\b",
            r"\bentry[- ]level\b",
            r"\bjunior\b",
        ]
        for pattern in strong:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.FALSE,
                    summary="High-confidence internship/junior signal",
                    evidence=match.group(0),
                )
        for pattern in review:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.UNKNOWN,
                    suggests_review=True,
                    summary="Ambiguous junior/internship wording",
                    evidence=match.group(0),
                )
        return _result(
            decision_id,
            code,
            RuleTriState.TRUE,
            summary="No internship/junior exclusion signal",
        )

    if code is ExclusionCode.VOLUNTEER:
        strong = [
            r"\bvolunteer assignment\b",
            r"\bunpaid volunteer\b",
            r"\bvolunteer position\b",
            r"\bvolunteer role\b",
        ]
        for pattern in strong:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.FALSE,
                    summary="Volunteer assignment indicated",
                    evidence=match.group(0),
                )
        if re.search(r"\bvolunteer\b", corpus):
            return _result(
                decision_id,
                code,
                RuleTriState.UNKNOWN,
                suggests_review=True,
                summary="Volunteer term present without strong context",
                evidence="volunteer",
            )
        return _result(
            decision_id,
            code,
            RuleTriState.TRUE,
            summary="No volunteer exclusion signal",
        )

    if code is ExclusionCode.NATIONAL_CONSULTANT_ONLY:
        strong = [
            r"\bnational consultant only\b",
            r"\bnationals only\b",
            r"\bfor nationals of\b",
            r"\bnational staff only\b",
            r"\blocal consultant only\b",
        ]
        review = [
            r"\bnational consultant\b",
            r"\bnational of\b",
            r"\blocal consultant\b",
        ]
        for pattern in strong:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.FALSE,
                    summary="Clear national/local-only restriction",
                    evidence=match.group(0),
                )
        for pattern in review:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.UNKNOWN,
                    suggests_review=True,
                    summary="Ambiguous national/local consultant wording",
                    evidence=match.group(0),
                )
        return _result(
            decision_id,
            code,
            RuleTriState.TRUE,
            summary="No national-only exclusion signal",
        )

    if code is ExclusionCode.REQUIRES_MULTI_PERSON_TEAM_OR_CONSORTIUM:
        strong = [
            r"\bconsortium required\b",
            r"\bconsortium of consultants\b",
            r"\bmulti[- ]person team\b",
            r"\bteam of consultants\b",
            r"\bminimum of \d+ consultants\b",
        ]
        review = [
            r"\bconsortium\b",
            r"\bteam leader\b",
            r"\bkey experts\b",
        ]
        for pattern in strong:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.FALSE,
                    summary="Clear multi-person team/consortium requirement",
                    evidence=match.group(0),
                )
        for pattern in review:
            match = re.search(pattern, corpus)
            if match:
                return _result(
                    decision_id,
                    code,
                    RuleTriState.UNKNOWN,
                    suggests_review=True,
                    summary="Suggestive team/consortium wording",
                    evidence=match.group(0),
                )
        return _result(
            decision_id,
            code,
            RuleTriState.TRUE,
            summary="No team/consortium exclusion signal",
        )

    return _result(
        decision_id,
        code,
        RuleTriState.UNKNOWN,
        summary="Unsupported exclusion code for evaluation",
    )
