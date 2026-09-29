"""Read-only: suggest five production pilot opportunities for Phase 17G-1B."""

from __future__ import annotations

import argparse
import json
import re
import sys

from _script_bootstrap import bootstrap_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (includes opportunity ids for later scripts)",
    )
    args = parser.parse_args(argv)
    bootstrap_repo()

    from jobhunter.application.profile_assessment.pilot_candidates import (
        PilotCategory,
        pick_one_per_category,
        score_pilot_categories,
    )
    from jobhunter.application.profile_assessment.source_sufficiency import (
        infer_source_data_sufficiency,
    )
    from jobhunter.application.review.source_links import pick_primary_source_link
    from jobhunter.infrastructure.importers.professional_services.identity import (
        PRIMARY_PROFILE_KEY,
    )
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.assessment_repositories import (
        OpportunityProfileAssessmentRepository,
    )
    from jobhunter.infrastructure.persistence.ranking_repositories import (
        OpportunityRankingRepository,
    )
    from jobhunter.infrastructure.persistence.repositories import (
        JobSourceRepository,
        OpportunityRepository,
        OpportunitySourceRepository,
    )
    from jobhunter.infrastructure.persistence.review_repositories import (
        OpportunityReviewRecordRepository,
    )
    from jobhunter.infrastructure.persistence.strategy_repositories import (
        SearchStrategyRepository,
    )

    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            strategy = SearchStrategyRepository(session).get_by_owner_key(
                PRIMARY_PROFILE_KEY
            )
            if strategy is None or strategy.current_revision_id is None:
                print("No active search strategy revision.", file=sys.stderr)
                return 1
            revision_id = strategy.current_revision_id

            opps = OpportunityRepository(session).list_all()
            job_source_repo = JobSourceRepository(session)
            opp_sources = OpportunitySourceRepository(session)
            assessments = OpportunityProfileAssessmentRepository(session)
            rankings = OpportunityRankingRepository(session)
            reviews = OpportunityReviewRecordRepository(session)

            candidates: list[dict] = []
            for opp in opps:
                scores = score_pilot_categories(opp.title, opp.description)
                links = opp_sources.list_for_opportunity(opp.id)
                primary_link = pick_primary_source_link(links, job_source_repo)
                source_label = primary_link.source_name if primary_link else None
                primary_source_id = primary_link.source_id if primary_link else None
                sufficiency = infer_source_data_sufficiency(
                    opp, primary_source_id=primary_source_id
                )

                opp_assessments = [
                    a
                    for a in assessments.list_for_opportunity(opp.id)
                    if a.search_strategy_revision_id == revision_id
                ]
                latest_success = None
                for a in reversed(opp_assessments):
                    if a.is_successful and a.model_provider != "fake":
                        latest_success = a
                        break
                overall = None
                schema_ver = None
                has_legacy_unknown = False
                if latest_success and latest_success.result:
                    overall = latest_success.result.get("overall_relevance")
                    schema_ver = latest_success.prompt_schema_version
                    if (
                        schema_ver
                        in ("profile_assessment_v1", "profile_assessment_v2")
                        and overall == "UNKNOWN"
                    ):
                        has_legacy_unknown = True

                ranking = rankings.find_current_ranked_for_revision(
                    opp.id, revision_id
                )
                band = ranking.priority_band.value if ranking else None
                review = reviews.get_latest_for_opportunity(opp.id)
                disposition = review.disposition.value if review else None

                title_blob = f"{opp.title} {(opp.description or '')}".lower()

                def _category_rank_bonus(cat: PilotCategory) -> int:
                    if cat is PilotCategory.LAND_LIS:
                        if re.search(
                            r"cadast|land administration|land information|land registry",
                            title_blob,
                        ):
                            return 10
                    if cat is PilotCategory.GIS_SDI:
                        if re.search(
                            r"\b(gis|geospatial|postgis|spatial data|sdi)\b",
                            title_blob,
                        ):
                            return 10
                        if re.search(r"cadastral|surveying", title_blob):
                            return 5
                    if cat is PilotCategory.NON_DOMAIN_ENGINEERING:
                        if re.search(r"civil engineer", title_blob):
                            return 10
                    if cat is PilotCategory.NON_DOMAIN_SPECIALIST:
                        if re.search(r"hsse|safeguard officer|gender", title_blob):
                            return 10
                    return 0

                for category in PilotCategory:
                    if scores[category] <= 0:
                        continue
                    rank_bonus = _category_rank_bonus(category)
                    candidates.append(
                        {
                            "category": category,
                            "opportunity_id": opp.id,
                            "title": opp.title,
                            "organisation": opp.organisation,
                            "source": source_label,
                            "source_data_sufficiency": sufficiency.value,
                            "existing_overall_relevance": overall,
                            "existing_schema_version": schema_ver,
                            "ranking_band": band,
                            "latest_review_disposition": disposition,
                            "category_score": scores[category],
                            "has_legacy_unknown": has_legacy_unknown,
                            "sort_key": (
                                1 if has_legacy_unknown else 0,
                                rank_bonus,
                                scores[category],
                                len(opp.description or ""),
                            ),
                        }
                    )

            selected = pick_one_per_category(candidates)
            if len(selected) < 5:
                print(
                    f"Warning: only {len(selected)} categories matched "
                    f"(expected 5).",
                    file=sys.stderr,
                )

            labels = {
                PilotCategory.LAND_LIS: "A land/LIS/cadastre",
                PilotCategory.GIS_SDI: "B GIS/SDI/geospatial",
                PilotCategory.DIGITAL_ADJACENT: "C digital/interoperability",
                PilotCategory.NON_DOMAIN_ENGINEERING: "D non-domain engineering",
                PilotCategory.NON_DOMAIN_SPECIALIST: "E non-domain specialist",
            }

            if args.json:
                payload = {
                    "search_strategy_revision_id": revision_id,
                    "pilot": [
                        {
                            "pilot_slot": labels[row["category"]],
                            "category": row["category"].value,
                            **{k: row[k] for k in row if k not in ("category", "sort_key", "category_score", "has_legacy_unknown")},
                        }
                        for row in selected
                    ],
                }
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0

            for row in selected:
                cat = row["category"]
                print(f"[{labels[cat]}] {row['opportunity_id']}")
                print(f"  title: {row['title'][:120]}")
                print(f"  organisation: {row['organisation'] or '—'}")
                print(f"  source: {row['source'] or '—'}")
                print(f"  source_data_sufficiency: {row['source_data_sufficiency']}")
                print(
                    f"  existing_overall_relevance: {row['existing_overall_relevance'] or '—'} "
                    f"({row['existing_schema_version'] or 'no assessment'})"
                )
                print(f"  ranking_band: {row['ranking_band'] or '—'}")
                print(
                    f"  latest_review_disposition: {row['latest_review_disposition'] or '—'}"
                )
                print()
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
