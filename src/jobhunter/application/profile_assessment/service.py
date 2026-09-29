"""Orchestrate opportunity profile/relevance assessment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from jobhunter.ai.protocol import AssessmentModel
from jobhunter.application.profile_assessment.context_builder import (
    ProfileEvidenceContextBuilder,
)
from jobhunter.application.profile_assessment.digests import (
    compute_input_digest,
    compute_opportunity_content_digest,
    compute_profile_evidence_digest,
    default_prompt_schema_version,
)
from jobhunter.application.profile_assessment.evidence_loader import (
    ProfessionalEvidenceLoader,
)
from jobhunter.application.opportunity_processing.structured_facts_loader import (
    OpportunityStructuredFactsLoader,
)
from jobhunter.application.profile_assessment.opportunity_prompt import (
    build_opportunity_prompt_text,
)
from jobhunter.application.profile_assessment.source_sufficiency import (
    infer_source_data_sufficiency,
)
from jobhunter.application.profile_assessment.validation import (
    AssessmentValidationService,
)
from jobhunter.domain.assessment_enums import (
    PROFILE_ASSESSMENT_SCHEMA_VERSION,
    AssessmentStatus,
)
from jobhunter.domain.assessment_request import AssessmentRequest
from jobhunter.domain.assessment_enums import SourceDataSufficiency
from jobhunter.domain.eligibility_enums import RuleTriState
from jobhunter.domain.enums import EligibilityStatus, LifecycleStatus
from jobhunter.domain.opportunity_profile_assessment import OpportunityProfileAssessment
from jobhunter.domain.strategy_enums import StrategyCriterionCategory
from jobhunter.infrastructure.importers.professional_services.identity import (
    PRIMARY_PROFILE_KEY,
)
from jobhunter.infrastructure.persistence.assessment_repositories import (
    OpportunityProfileAssessmentRepository,
)
from jobhunter.infrastructure.persistence.eligibility_repositories import (
    EligibilityDecisionRepository,
    EligibilityRuleResultRepository,
)
from jobhunter.infrastructure.persistence.profile_repositories import (
    AssignmentCapabilityRepository,
)
from jobhunter.infrastructure.persistence.repositories import (
    OpportunityRepository,
    OpportunitySourceRepository,
)
from jobhunter.infrastructure.persistence.strategy_repositories import (
    SearchStrategyRepository,
    StrategyRevisionSnapshotRepository,
)


@dataclass(slots=True)
class ProfileAssessmentOutcome:
    assessment: OpportunityProfileAssessment | None
    reused: bool
    skipped: bool
    skip_reason: str | None = None


class OpportunityProfileAssessmentService:
    def __init__(
        self,
        session: Session,
        model: AssessmentModel,
    ) -> None:
        self._session = session
        self._model = model
        self._opportunities = OpportunityRepository(session)
        self._sources = OpportunitySourceRepository(session)
        self._assessments = OpportunityProfileAssessmentRepository(session)
        self._eligibility_decisions = EligibilityDecisionRepository(session)
        self._eligibility_rules = EligibilityRuleResultRepository(session)
        self._strategies = SearchStrategyRepository(session)
        self._snapshots = StrategyRevisionSnapshotRepository(session)
        self._evidence_loader = ProfessionalEvidenceLoader(session)
        self._assignment_capabilities = AssignmentCapabilityRepository(session)
        self._context_builder = ProfileEvidenceContextBuilder()
        self._validator = AssessmentValidationService()
        self._structured_facts = OpportunityStructuredFactsLoader(session)

    def assess_opportunity(
        self,
        opportunity_id: str,
        *,
        owner_key: str = PRIMARY_PROFILE_KEY,
        revision_id: str | None = None,
        force: bool = False,
        include_ineligible: bool = False,
        dry_run: bool = False,
        assessed_at: datetime | None = None,
    ) -> ProfileAssessmentOutcome:
        when = assessed_at or datetime.now(timezone.utc)
        opportunity = self._opportunities.get_by_id(opportunity_id)
        if opportunity is None:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        if not force and opportunity.lifecycle_status in (
            LifecycleStatus.EXPIRED,
            LifecycleStatus.CLOSED,
        ):
            return ProfileAssessmentOutcome(
                None, False, True, "lifecycle_closed_or_expired"
            )

        snapshot = self._resolve_snapshot(owner_key, revision_id)
        decisions = self._eligibility_decisions.list_for_opportunity(opportunity_id)
        latest_decision = decisions[-1] if decisions else None
        eligibility_status = (
            latest_decision.status
            if latest_decision is not None
            else opportunity.eligibility_status
        )

        if (
            eligibility_status is EligibilityStatus.INELIGIBLE
            and not include_ineligible
            and not force
        ):
            return ProfileAssessmentOutcome(
                None, False, True, "ineligible_gated"
            )

        catalog = self._evidence_loader.load_primary()
        structured_facts = self._structured_facts.load_for_opportunity(
            opportunity_id
        )
        opportunity_digest = compute_opportunity_content_digest(
            opportunity, structured_facts
        )
        profile_digest = compute_profile_evidence_digest(
            catalog.profile,
            catalog.services,
            catalog.assignments,
            catalog.capabilities,
            catalog.skills,
            catalog.languages,
            catalog.countries,
        )
        input_digest = compute_input_digest(
            opportunity_content_digest=opportunity_digest,
            profile_evidence_digest=profile_digest,
            search_strategy_revision_id=snapshot.revision.id,
            prompt_schema_version=default_prompt_schema_version(),
            model_provider=self._model.provider,
            model_name=self._model.model_name,
        )

        existing = self._assessments.find_reusable_success(
            opportunity_id, input_digest
        )
        if existing is not None and not force:
            return ProfileAssessmentOutcome(existing, True, False)

        primary_source_id = self._primary_source_id(opportunity_id)
        sufficiency = infer_source_data_sufficiency(
            opportunity, primary_source_id=primary_source_id
        )
        pack = self._context_builder.build(
            opportunity,
            catalog,
            self._assignment_capabilities.list_all(),
        )
        prompt_text = build_opportunity_prompt_text(opportunity, structured_facts)
        rule_summaries = self._eligibility_summaries(latest_decision)
        themes = [
            theme.to_mapping()
            for theme in snapshot.themes
            if theme.is_active
        ]
        preferences = [
            criterion.to_mapping()
            for criterion in snapshot.criteria
            if criterion.is_active
            and criterion.category is StrategyCriterionCategory.PREFERENCE
        ]
        allowed_theme_keys = {theme["theme_key"] for theme in themes}

        request = AssessmentRequest(
            schema_version=PROFILE_ASSESSMENT_SCHEMA_VERSION,
            opportunity=opportunity.to_mapping(),
            opportunity_prompt_text=prompt_text,
            source_data_sufficiency=sufficiency,
            evidence_pack=pack,
            search_themes=themes,
            preference_criteria=preferences,
            eligibility_rule_summaries=rule_summaries,
            instructions=self._instructions_for_sufficiency(sufficiency),
        )

        if dry_run:
            return ProfileAssessmentOutcome(
                OpportunityProfileAssessment(
                    opportunity_id=opportunity_id,
                    search_strategy_revision_id=snapshot.revision.id,
                    eligibility_decision_id=(
                        latest_decision.id if latest_decision else None
                    ),
                    assessed_at=when,
                    status=AssessmentStatus.SUCCEEDED,
                    input_digest=input_digest,
                    opportunity_content_digest=opportunity_digest,
                    profile_evidence_digest=profile_digest,
                    prompt_schema_version=default_prompt_schema_version(),
                    model_provider=self._model.provider,
                    model_name=self._model.model_name,
                    result={"dry_run": True, "request": request.to_mapping()},
                ),
                False,
                False,
            )

        model_response = self._model.assess(request)
        if model_response.error:
            assessment = OpportunityProfileAssessment(
                opportunity_id=opportunity_id,
                search_strategy_revision_id=snapshot.revision.id,
                eligibility_decision_id=(
                    latest_decision.id if latest_decision else None
                ),
                assessed_at=when,
                status=AssessmentStatus.FAILED_PROVIDER,
                input_digest=input_digest,
                opportunity_content_digest=opportunity_digest,
                profile_evidence_digest=profile_digest,
                prompt_schema_version=default_prompt_schema_version(),
                model_provider=model_response.provider,
                model_name=model_response.model_name,
                provider_error=model_response.error,
            )
            saved = self._assessments.save(assessment)
            return ProfileAssessmentOutcome(saved, False, False)

        raw = model_response.parsed
        if raw is None:
            try:
                raw = json.loads(model_response.raw_text or "{}")
            except json.JSONDecodeError:
                raw = None

        if not isinstance(raw, dict):
            assessment = OpportunityProfileAssessment(
                opportunity_id=opportunity_id,
                search_strategy_revision_id=snapshot.revision.id,
                eligibility_decision_id=(
                    latest_decision.id if latest_decision else None
                ),
                assessed_at=when,
                status=AssessmentStatus.FAILED_VALIDATION,
                input_digest=input_digest,
                opportunity_content_digest=opportunity_digest,
                profile_evidence_digest=profile_digest,
                prompt_schema_version=default_prompt_schema_version(),
                model_provider=model_response.provider,
                model_name=model_response.model_name,
                provider_error="model output was not a JSON object",
            )
            saved = self._assessments.save(assessment)
            return ProfileAssessmentOutcome(saved, False, False)

        validation = self._validator.validate(
            raw, request, allowed_theme_keys=allowed_theme_keys
        )
        if validation.failed or validation.result is None:
            assessment = OpportunityProfileAssessment(
                opportunity_id=opportunity_id,
                search_strategy_revision_id=snapshot.revision.id,
                eligibility_decision_id=(
                    latest_decision.id if latest_decision else None
                ),
                assessed_at=when,
                status=AssessmentStatus.FAILED_VALIDATION,
                input_digest=input_digest,
                opportunity_content_digest=opportunity_digest,
                profile_evidence_digest=profile_digest,
                prompt_schema_version=default_prompt_schema_version(),
                model_provider=model_response.provider,
                model_name=model_response.model_name,
                validation_warnings=validation.warnings,
                provider_error="structured output failed validation",
            )
            saved = self._assessments.save(assessment)
            return ProfileAssessmentOutcome(saved, False, False)

        status = (
            AssessmentStatus.SUCCEEDED_WITH_WARNINGS
            if validation.warnings
            else AssessmentStatus.SUCCEEDED
        )
        assessment = OpportunityProfileAssessment(
            opportunity_id=opportunity_id,
            search_strategy_revision_id=snapshot.revision.id,
            eligibility_decision_id=(
                latest_decision.id if latest_decision else None
            ),
            assessed_at=when,
            status=status,
            input_digest=input_digest,
            opportunity_content_digest=opportunity_digest,
            profile_evidence_digest=profile_digest,
            prompt_schema_version=default_prompt_schema_version(),
            model_provider=model_response.provider,
            model_name=model_response.model_name,
            validation_warnings=validation.warnings,
            result=validation.result.to_mapping(),
        )
        saved = self._assessments.save(assessment)
        return ProfileAssessmentOutcome(saved, False, False)

    def _resolve_snapshot(self, owner_key: str, revision_id: str | None):
        if revision_id is not None:
            snapshot = self._snapshots.load_snapshot(revision_id)
            if snapshot is None:
                raise ValueError(f"Revision {revision_id} not found")
            return snapshot
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

    def _primary_source_id(self, opportunity_id: str) -> str | None:
        links = self._sources.list_for_opportunity(opportunity_id)
        if not links:
            return None
        return links[0].source_id

    def _eligibility_summaries(self, decision) -> list[dict[str, str]]:
        if decision is None:
            return []
        rules = self._eligibility_rules.list_for_decision(decision.id)
        summaries: list[dict[str, str]] = []
        for rule in rules:
            if rule.outcome is RuleTriState.UNKNOWN or rule.suggests_review:
                summaries.append(
                    {
                        "rule_kind": rule.rule_kind.value,
                        "rule_code": rule.rule_code,
                        "outcome": rule.outcome.value,
                        "summary": rule.summary or "",
                        "evidence": rule.evidence or "",
                    }
                )
        return summaries

    @staticmethod
    def _instructions_for_sufficiency(
        sufficiency: SourceDataSufficiency,
    ) -> str:
        if sufficiency is SourceDataSufficiency.LIST_SUMMARY_ONLY:
            return (
                "Opportunity text is a list-derived summary only. Do not infer missing "
                "ToR requirements, qualifications, durations, or team structure."
            )
        return (
            "Assess professional relevance against the Geo-ICT / land administration / "
            "LIS-GIS profile in evidence_pack. Use OUT_OF_SCOPE for clearly unrelated "
            "professional disciplines when the posting describes that discipline. "
            "Reserve UNKNOWN for genuinely insufficient source text, not for poor fit."
        )
