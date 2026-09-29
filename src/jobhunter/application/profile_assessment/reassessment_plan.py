"""Determine which opportunities need a paid profile assessment (read-only planning)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from jobhunter.ai.protocol import AssessmentModel
from jobhunter.application.opportunity_processing.structured_facts_loader import (
    OpportunityStructuredFactsLoader,
)
from jobhunter.application.profile_assessment.context_builder import (
    ProfileEvidenceContextBuilder,
)
from jobhunter.application.profile_assessment.digests import (
    compute_input_digest,
    compute_model_evidence_digest,
    compute_opportunity_content_digest,
    compute_profile_evidence_digest,
    default_prompt_schema_version,
)
from jobhunter.application.profile_assessment.evidence_loader import (
    ProfessionalEvidenceLoader,
)
from jobhunter.application.review.lifecycle import is_actionable_lifecycle
from jobhunter.domain.enums import EligibilityStatus
from jobhunter.domain.opportunity import Opportunity
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentCapabilityRepository,
)
from jobhunter.infrastructure.persistence.repositories import OpportunityRepository
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    StrategyRevisionSnapshotRepository,
)


@dataclass(slots=True)
class ReassessmentPlanRow:
    opportunity_id: str
    title: str
    lifecycle_status: str
    eligibility_status: str
    latest_schema: str | None
    would_reuse: bool
    skip_reason: str | None


@dataclass(slots=True)
class ReassessmentPopulationSummary:
    total_opportunities: int
    actionable_eligible: int
    by_lifecycle: dict[str, int]
    by_eligibility: dict[str, int]
    latest_success_schema: dict[str, int]
    needs_paid_assessment: int
    would_reuse_v3: int
    excluded_ineligible: int
    excluded_non_actionable_lifecycle: int
    rows: list[ReassessmentPlanRow]


def build_reassessment_population(
    session: Session,
    model: AssessmentModel,
    *,
    owner_key: str = PRIMARY_PROFILE_KEY,
) -> ReassessmentPopulationSummary:
    """Opportunities that would invoke OpenAI when assessed without --force."""
    opportunities = OpportunityRepository(session).list_all()
    strategy = SearchStrategyRepository(session).get_by_owner_key(owner_key)
    if strategy is None or strategy.current_revision_id is None:
        raise RuntimeError("No active search strategy revision")
    revision_id = strategy.current_revision_id
    snapshot = StrategyRevisionSnapshotRepository(session).load_snapshot(
        revision_id
    )
    if snapshot is None:
        raise RuntimeError("Strategy snapshot missing")

    catalog = ProfessionalEvidenceLoader(session).load_primary()
    assignment_caps = AssignmentCapabilityRepository(session).list_all()
    context_builder = ProfileEvidenceContextBuilder()
    structured_loader = OpportunityStructuredFactsLoader(session)
    assessments = OpportunityProfileAssessmentRepository(session)

    profile_digest = compute_profile_evidence_digest(
        catalog.profile,
        catalog.services,
        catalog.assignments,
        catalog.capabilities,
        catalog.skills,
        catalog.languages,
        catalog.countries,
    )
    schema_version = default_prompt_schema_version()

    by_lifecycle: dict[str, int] = {}
    by_eligibility: dict[str, int] = {}
    latest_schema: dict[str, int] = {}
    excluded_ineligible = 0
    excluded_lifecycle = 0
    actionable_eligible = 0
    needs_paid = 0
    would_reuse = 0
    plan_rows: list[ReassessmentPlanRow] = []

    for opp in opportunities:
        by_lifecycle[opp.lifecycle_status.value] = (
            by_lifecycle.get(opp.lifecycle_status.value, 0) + 1
        )
        by_eligibility[opp.eligibility_status.value] = (
            by_eligibility.get(opp.eligibility_status.value, 0) + 1
        )

        success_rows = [
            a
            for a in assessments.list_for_opportunity(opp.id)
            if a.search_strategy_revision_id == revision_id
            and a.is_successful
            and a.model_provider != "fake"
        ]
        latest = success_rows[-1] if success_rows else None
        latest_key = latest.prompt_schema_version if latest else "none"
        latest_schema[latest_key] = latest_schema.get(latest_key, 0) + 1

        if not is_actionable_lifecycle(opp.lifecycle_status):
            excluded_lifecycle += 1
            continue

        if opp.eligibility_status is not EligibilityStatus.ELIGIBLE:
            excluded_ineligible += 1
            continue

        actionable_eligible += 1
        input_digest = _input_digest_for(
            opp,
            catalog,
            assignment_caps,
            context_builder,
            structured_loader,
            profile_digest,
            snapshot.revision.id,
            schema_version,
            model,
        )
        reusable = assessments.find_reusable_success(opp.id, input_digest)
        if reusable is not None:
            would_reuse += 1
            plan_rows.append(
                _row(opp, latest, would_reuse=True, skip_reason=None)
            )
        else:
            needs_paid += 1
            plan_rows.append(
                _row(opp, latest, would_reuse=False, skip_reason="digest_or_schema_stale")
            )

    return ReassessmentPopulationSummary(
        total_opportunities=len(opportunities),
        actionable_eligible=actionable_eligible,
        by_lifecycle=by_lifecycle,
        by_eligibility=by_eligibility,
        latest_success_schema=latest_schema,
        needs_paid_assessment=needs_paid,
        would_reuse_v3=would_reuse,
        excluded_ineligible=excluded_ineligible,
        excluded_non_actionable_lifecycle=excluded_lifecycle,
        rows=plan_rows,
    )


def _row(
    opp: Opportunity,
    latest,
    *,
    would_reuse: bool,
    skip_reason: str | None,
) -> ReassessmentPlanRow:
    return ReassessmentPlanRow(
        opportunity_id=opp.id,
        title=opp.title,
        lifecycle_status=opp.lifecycle_status.value,
        eligibility_status=opp.eligibility_status.value,
        latest_schema=latest.prompt_schema_version if latest else None,
        would_reuse=would_reuse,
        skip_reason=skip_reason,
    )


def _input_digest_for(
    opp: Opportunity,
    catalog,
    assignment_caps,
    context_builder,
    structured_loader,
    profile_digest: str,
    revision_id: str,
    schema_version: str,
    model: AssessmentModel,
) -> str:
    structured = structured_loader.load_for_opportunity(opp.id)
    opportunity_digest = compute_opportunity_content_digest(opp, structured)
    pack = context_builder.build(opp, catalog, assignment_caps)
    model_digest = compute_model_evidence_digest(pack)
    return compute_input_digest(
        opportunity_content_digest=opportunity_digest,
        profile_evidence_digest=profile_digest,
        model_evidence_digest=model_digest,
        search_strategy_revision_id=revision_id,
        prompt_schema_version=schema_version,
        model_provider=model.provider,
        model_name=model.model_name,
    )
