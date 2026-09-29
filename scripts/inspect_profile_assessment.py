"""Read-only inspection of profile assessment results and model evidence selection."""

from __future__ import annotations

import argparse
import json
import sys

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--opportunity-id",
        action="append",
        dest="opportunity_ids",
        required=True,
        help="Repeat for multiple opportunities",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    bootstrap_repo()

    from jobhunter.application.profile_assessment.context_builder import (
        ProfileEvidenceContextBuilder,
    )
    from jobhunter.application.profile_assessment.evidence_loader import (
        ProfessionalEvidenceLoader,
    )
    from jobhunter.application.profile_assessment.source_sufficiency import (
        infer_source_data_sufficiency,
    )
    from jobhunter.application.review.opportunity_reads import OpportunityPipelineReader
    from jobhunter.infrastructure.importers.professional_services.identity import (
        PRIMARY_PROFILE_KEY,
    )
    from jobhunter.infrastructure.config import get_settings
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
    )

    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    reports: list[dict] = []
    try:
        with session_scope(session_factory) as session:
            strategy = SearchStrategyRepository(session).get_by_owner_key(
                PRIMARY_PROFILE_KEY
            )
            if strategy is None or strategy.current_revision_id is None:
                print("No active search strategy revision.", file=sys.stderr)
                return 1
            revision_id = strategy.current_revision_id

            pipeline = OpportunityPipelineReader(session)
            context_builder = ProfileEvidenceContextBuilder()
            evidence_loader = ProfessionalEvidenceLoader(session)
            assignment_caps = AssignmentCapabilityRepository(session).list_all()
            catalog = evidence_loader.load_primary()
            opp_repo = OpportunityRepository(session)
            sources = OpportunitySourceRepository(session)

            for opp_id in args.opportunity_ids:
                opp = opp_repo.get_by_id(opp_id)
                if opp is None:
                    print(f"Unknown opportunity: {opp_id}", file=sys.stderr)
                    return 1

                pipe = pipeline.load(opp, revision_id, allow_fake=False)
                assessment = pipe.display_assessment
                ranking = pipe.display_ranking

                result = assessment.result if assessment else {}
                prof_rel = result.get("professional_relevance") or {}
                scope_summary = prof_rel.get("scope_summary")

                links = sources.list_for_opportunity(opp_id)
                primary_source_id = links[0].source_id if links else None
                sufficiency = infer_source_data_sufficiency(
                    opp, primary_source_id=primary_source_id
                )

                pack = context_builder.build(opp, catalog, assignment_caps)
                selected_assignments = [
                    {"id": a.id, "title": a.project_name or a.role}
                    for a in pack.assignments
                ]
                selected_services = [
                    {"id": s.id, "name": s.name}
                    for s in pack.professional_services
                ]

                reports.append(
                    {
                        "opportunity_id": opp_id,
                        "title": opp.title,
                        "assessment_status": assessment.status.value
                        if assessment
                        else None,
                        "schema_version": assessment.prompt_schema_version
                        if assessment
                        else None,
                        "model": (
                            f"{assessment.model_provider}/{assessment.model_name}"
                            if assessment
                            else None
                        ),
                        "source_data_sufficiency": sufficiency.value,
                        "overall_relevance": result.get("overall_relevance"),
                        "professional_relevance_scope_summary": scope_summary,
                        "rationale": result.get("rationale"),
                        "prompt_tokens": assessment.prompt_tokens if assessment else None,
                        "completion_tokens": assessment.completion_tokens
                        if assessment
                        else None,
                        "total_tokens": assessment.total_tokens if assessment else None,
                        "ranking_status": ranking.status.value if ranking else None,
                        "ranking_score": ranking.internal_sort_score
                        if ranking
                        else None,
                        "ranking_band": ranking.priority_band.value
                        if ranking
                        else None,
                        "selected_assignments": selected_assignments,
                        "selected_professional_services": selected_services,
                    }
                )

        if args.json:
            print(json.dumps(reports, indent=2, ensure_ascii=False))
            return 0

        for row in reports:
            print(f"{row['opportunity_id']} — {row['title'][:100]}")
            print(f"  status: {row['assessment_status']}")
            print(f"  schema: {row['schema_version']}  model: {row['model']}")
            print(f"  source_data_sufficiency: {row['source_data_sufficiency']}")
            print(f"  overall_relevance: {row['overall_relevance']}")
            print(f"  scope_summary: {row['professional_relevance_scope_summary']}")
            print(f"  rationale: {(row['rationale'] or '')[:240]}")
            print(
                f"  tokens: prompt={row['prompt_tokens']} "
                f"completion={row['completion_tokens']} total={row['total_tokens']}"
            )
            print(
                f"  ranking: {row['ranking_status']} "
                f"score={row['ranking_score']} band={row['ranking_band']}"
            )
            print(f"  selected_assignments: {row['selected_assignments']}")
            print(f"  selected_services: {row['selected_professional_services']}")
            print()
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
