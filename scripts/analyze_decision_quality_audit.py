"""Phase 17G-0 read-only decision-quality audit (no DB writes).

Run from repo root: python scripts/analyze_decision_quality_audit.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(slots=True)
class OppSnapshot:
    opportunity_id: str
    title: str
    eligibility_status: str
    lifecycle_status: str
    source_id: str | None
    assessment_status: str | None
    overall_relevance: str | None
    priority_band: str | None
    ranking_status: str | None
    internal_sort_score: int | None
    review_disposition: str | None
    scope_summary: str | None
    source_data_sufficiency: str | None
    in_default_queue: bool


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    _load_env(root / ".env")
    sys.path.insert(0, str(root / "src"))

    from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
    from jobhunter.application.review.dtos import OpportunityQueueFilters
    from jobhunter.application.review.lifecycle import is_actionable_lifecycle
    from jobhunter.application.review.opportunity_query import OpportunityReviewQueryService
    from jobhunter.application.review.production_selection import select_production_ranking
    from jobhunter.domain.enums import EligibilityStatus
    from jobhunter.domain.ranking_enums import RankingStatus
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.assessment_repositories import (
        OpportunityProfileAssessmentRepository,
    )
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    from jobhunter.infrastructure.persistence.ranking_repositories import (
        OpportunityRankingRepository,
    )
    from jobhunter.infrastructure.persistence.repositories import (
        OpportunityRepository,
        OpportunitySourceRepository,
    )
    from jobhunter.infrastructure.persistence.review_repositories import (
        OpportunityReviewRecordRepository,
    )

    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    default_filters = OpportunityQueueFilters(allow_fake=False)

    with session_scope(session_factory) as session:
        ctx = ActiveSearchStrategyResolver(session).resolve()
        revision_id = ctx.revision_id
        opps = OpportunityRepository(session).list_all()
        assessments = OpportunityProfileAssessmentRepository(session).list_for_revision(
            revision_id
        )
        rankings = OpportunityRankingRepository(session).list_for_revision(revision_id)
        reviews = OpportunityReviewRecordRepository(session).map_latest_by_opportunity_ids(
            [o.id for o in opps]
        )
        sources = OpportunitySourceRepository(session)
        queue_items = {
            item.opportunity_id: item
            for item in OpportunityReviewQueryService(session).list_queue(default_filters)
        }

        assessment_by_id = {a.id: a for a in assessments if a.id}
        assessments_by_opp: dict[str, list] = defaultdict(list)
        for row in assessments:
            assessments_by_opp[row.opportunity_id].append(row)

        rankings_by_opp: dict[str, list] = defaultdict(list)
        for row in rankings:
            rankings_by_opp[row.opportunity_id].append(row)

        snapshots: list[OppSnapshot] = []
        for opp in opps:
            opp_assessments = sorted(
                assessments_by_opp.get(opp.id, []),
                key=lambda r: r.assessed_at,
            )
            production_assessment = None
            for row in reversed(opp_assessments):
                if row.model_provider == "fake":
                    continue
                if row.status.value in ("SUCCEEDED", "SUCCEEDED_WITH_WARNINGS"):
                    production_assessment = row
                    break

            opp_rankings = sorted(
                rankings_by_opp.get(opp.id, []),
                key=lambda r: r.ranked_at,
                reverse=True,
            )
            display_ranking = select_production_ranking(
                opp_rankings, assessment_by_id, allow_fake=False
            )

            result = (production_assessment.result or {}) if production_assessment else {}
            prof = result.get("professional_relevance") or {}
            primary_source = sources.list_for_opportunity(opp.id)
            source_id = primary_source[0].source_id if primary_source else None

            review = reviews.get(opp.id)
            in_queue = opp.id in queue_items
            snapshots.append(
                OppSnapshot(
                    opportunity_id=opp.id,
                    title=opp.title,
                    eligibility_status=opp.eligibility_status.value,
                    lifecycle_status=opp.lifecycle_status.value,
                    source_id=source_id,
                    assessment_status=(
                        production_assessment.status.value
                        if production_assessment
                        else None
                    ),
                    overall_relevance=str(result.get("overall_relevance"))
                    if result.get("overall_relevance")
                    else None,
                    priority_band=(
                        display_ranking.priority_band.value
                        if display_ranking and display_ranking.priority_band
                        else None
                    ),
                    ranking_status=(
                        display_ranking.status.value if display_ranking else None
                    ),
                    internal_sort_score=(
                        display_ranking.internal_sort_score if display_ranking else None
                    ),
                    review_disposition=(
                        review.disposition.value if review else None
                    ),
                    scope_summary=str(prof.get("scope_summary") or "")[:500] or None,
                    source_data_sufficiency=str(
                        result.get("source_data_sufficiency") or ""
                    )
                    or None,
                    in_default_queue=in_queue,
                )
            )

    def disposition_label(d: str | None) -> str:
        return d if d else "UNREVIEWED"

    ranked = [s for s in snapshots if s.ranking_status == RankingStatus.RANKED.value]

    cross = Counter(
        (s.priority_band or "NONE", disposition_label(s.review_disposition))
        for s in ranked
    )

    overall_rel_dist = Counter(
        s.overall_relevance or "NONE" for s in snapshots if s.assessment_status
    )
    unranked = [s for s in snapshots if s.ranking_status == RankingStatus.UNRANKED.value]
    excluded = [s for s in snapshots if s.ranking_status == RankingStatus.EXCLUDED.value]

    report = {
        "revision_id": revision_id,
        "total_opportunities": len(snapshots),
        "default_queue_count": sum(1 for s in snapshots if s.in_default_queue),
        "by_eligibility": dict(Counter(s.eligibility_status for s in snapshots)),
        "by_ranking_band_ranked_only": dict(
            Counter(s.priority_band for s in ranked if s.priority_band)
        ),
        "by_assessment_overall_relevance": dict(
            Counter(s.overall_relevance or "NONE" for s in snapshots)
        ),
        "production_assessment_overall_relevance": dict(overall_rel_dist),
        "unranked_count": len(unranked),
        "excluded_ranking_count": len(excluded),
        "investigate_disposition_count": sum(
            1 for s in snapshots if s.review_disposition == "INVESTIGATE"
        ),
        "by_review_disposition": dict(
            Counter(disposition_label(s.review_disposition) for s in snapshots)
        ),
        "band_x_disposition_ranked": {f"{a}|{b}": c for (a, b), c in cross.items()},
        "required_cells": {
            "LOW|DISMISS": cross.get(("LOW", "DISMISS"), 0),
            "LOW|SHORTLIST": cross.get(("LOW", "SHORTLIST"), 0),
            "LOW|UNREVIEWED": cross.get(("LOW", "UNREVIEWED"), 0),
            "MEDIUM|DISMISS": cross.get(("MEDIUM", "DISMISS"), 0),
            "HIGH|DISMISS": cross.get(("HIGH", "DISMISS"), 0),
            "MEDIUM|SHORTLIST": cross.get(("MEDIUM", "SHORTLIST"), 0),
            "HIGH|SHORTLIST": cross.get(("HIGH", "SHORTLIST"), 0),
        },
        "low_dismiss_samples": [],
        "medium_high_dismiss_samples": [],
        "low_unreviewed_diagnostic": Counter(),
        "shortlist_positive_controls": [],
        "proposed_gate_estimate": Counter(),
    }

    def sample_row(s: OppSnapshot) -> dict:
        return {
            "id": s.opportunity_id,
            "title": s.title[:120],
            "band": s.priority_band,
            "overall_relevance": s.overall_relevance,
            "eligibility": s.eligibility_status,
            "score": s.internal_sort_score,
            "scope_summary": s.scope_summary,
            "source": s.source_id,
            "sufficiency": s.source_data_sufficiency,
        }

    for s in ranked:
        if s.priority_band == "LOW" and s.review_disposition == "DISMISS":
            if len(report["low_dismiss_samples"]) < 25:
                report["low_dismiss_samples"].append(sample_row(s))
        if s.priority_band in ("MEDIUM", "HIGH") and s.review_disposition == "DISMISS":
            if len(report["medium_high_dismiss_samples"]) < 15:
                report["medium_high_dismiss_samples"].append(sample_row(s))
        if s.review_disposition == "SHORTLIST":
            if len(report["shortlist_positive_controls"]) < 20:
                report["shortlist_positive_controls"].append(sample_row(s))

    # Diagnostic classifier (analysis-only heuristic for 17G planning)
    def diagnose_low_unreviewed(s: OppSnapshot) -> str:
        title_l = s.title.lower()
        rel = (s.overall_relevance or "").upper()
        scope = (s.scope_summary or "").lower()
        if rel == "OUT_OF_SCOPE":
            return "professionally_irrelevant"
        if rel in ("WEAK_FIT", "MODERATE_FIT", "STRONG_FIT"):
            if any(
                k in title_l
                for k in (
                    "hsse",
                    "safeguard",
                    "gender",
                    "social inclusion",
                    "civil engineer",
                    "audit expert",
                    "evaluation",
                    "climate resilience",
                    "environmental specialist",
                )
            ):
                return "adjacent_or_mismatch_title_vs_assessment"
            return "relevant_but_weak_fit"
        if rel in ("INSUFFICIENT_EVIDENCE", "UNKNOWN", ""):
            if s.source_data_sufficiency == "LIST_SUMMARY_ONLY":
                return "insufficient_source_data"
            return "insufficient_source_data"
        if "out of scope" in scope or "unrelated" in scope:
            return "professionally_irrelevant"
        return "other"

    for s in ranked:
        if s.priority_band == "LOW" and s.review_disposition is None:
            bucket = diagnose_low_unreviewed(s)
            report["low_unreviewed_diagnostic"][bucket] += 1

    def proposed_relevance_gate(s: OppSnapshot) -> str:
        """Conceptual gate: hide from default queue, keep in audit."""
        rel = (s.overall_relevance or "UNKNOWN").upper()
        if rel == "OUT_OF_SCOPE":
            return "PROFESSIONALLY_IRRELEVANT"
        if rel in ("UNKNOWN", "INSUFFICIENT_EVIDENCE"):
            return "NEEDS_EVIDENCE_OR_REVIEW"
        score = s.internal_sort_score or 0
        if rel == "WEAK_FIT" and score < 220:
            return "MARGINAL_RELEVANCE"
        return "QUEUE_AS_TODAY"

    for s in snapshots:
        if s.in_default_queue:
            report["proposed_gate_estimate"][proposed_relevance_gate(s)] += 1

    import re

    geo_patterns = [
        r"\bgis\b",
        r"geospatial",
        r"cadast",
        r"land administration",
        r"land information",
        r"spatial data",
        r"\blis\b",
        r"land registry",
        r"cadastr",
        r"\bmapping\b",
    ]
    report["geo_relevant_title_candidates"] = []
    for s in snapshots:
        title_l = s.title.lower()
        if any(re.search(pat, title_l) for pat in geo_patterns):
            report["geo_relevant_title_candidates"].append(sample_row(s))

    out_path = root / "docs" / "analysis" / "phase-17g-0-audit-data.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report["required_cells"], indent=2))
    print(f"total_opportunities={report['total_opportunities']}")
    print(f"default_queue_count={report['default_queue_count']}")
    print(f"wrote {out_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
