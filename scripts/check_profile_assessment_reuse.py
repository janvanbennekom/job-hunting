"""Read-only: check whether input_digest matches a reusable successful assessment."""

from __future__ import annotations

import argparse
import sys

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opportunity-id", required=True)
    args = parser.parse_args(argv)
    bootstrap_repo()

    from jobhunter.ai.factory import resolve_assessment_model
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
    from jobhunter.application.opportunity_processing.structured_facts_loader import (
        OpportunityStructuredFactsLoader,
    )
    from jobhunter.infrastructure.importers.professional_services.identity import (
        PRIMARY_PROFILE_KEY,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.assessment_repositories import (
        OpportunityProfileAssessmentRepository,
    )
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
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

    settings = get_settings()
    settings.require_database_url()
    model = resolve_assessment_model(settings, "openai")
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            opp = OpportunityRepository(session).get_by_id(args.opportunity_id)
            if opp is None:
                print(f"Unknown opportunity: {args.opportunity_id}", file=sys.stderr)
                return 1

            strategy = SearchStrategyRepository(session).get_by_owner_key(
                PRIMARY_PROFILE_KEY
            )
            if strategy is None or strategy.current_revision_id is None:
                print("No active search strategy revision.", file=sys.stderr)
                return 1
            snapshot = StrategyRevisionSnapshotRepository(session).load_snapshot(
                strategy.current_revision_id
            )
            if snapshot is None:
                print("Strategy snapshot missing.", file=sys.stderr)
                return 1

            catalog = ProfessionalEvidenceLoader(session).load_primary()
            structured = OpportunityStructuredFactsLoader(session).load_for_opportunity(
                opp.id
            )
            opportunity_digest = compute_opportunity_content_digest(opp, structured)
            profile_digest = compute_profile_evidence_digest(
                catalog.profile,
                catalog.services,
                catalog.assignments,
                catalog.capabilities,
                catalog.skills,
                catalog.languages,
                catalog.countries,
            )
            pack = ProfileEvidenceContextBuilder().build(
                opp,
                catalog,
                AssignmentCapabilityRepository(session).list_all(),
            )
            model_digest = compute_model_evidence_digest(pack)
            input_digest = compute_input_digest(
                opportunity_content_digest=opportunity_digest,
                profile_evidence_digest=profile_digest,
                model_evidence_digest=model_digest,
                search_strategy_revision_id=snapshot.revision.id,
                prompt_schema_version=default_prompt_schema_version(),
                model_provider=model.provider,
                model_name=model.model_name,
            )

            repo = OpportunityProfileAssessmentRepository(session)
            existing = repo.find_reusable_success(opp.id, input_digest)
            if existing is None:
                print(
                    "reuse: no — no successful assessment with current input_digest "
                    "(a live run would call the provider)"
                )
                return 0

            print(
                f"reuse: yes — assessment_id={existing.id} "
                f"schema={existing.prompt_schema_version} "
                f"assessed_at={existing.assessed_at.isoformat()}"
            )
            print(f"input_digest: {input_digest[:16]}…")
            links = OpportunitySourceRepository(session).list_for_opportunity(opp.id)
            if links:
                print(
                    "Tip: `assess_opportunity_profile.py --opportunity-id …` "
                    "without --force should return (reused) without a provider call."
                )
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
