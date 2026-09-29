"""Phase 17G-2A read-only v4 decision-quality audit (no OpenAI, no DB writes).

Run from repo root:
  python scripts/analyze_v4_decision_quality.py
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from _script_bootstrap import bootstrap_repo

V4_SCHEMA = "profile_assessment_v4"
CALIBRATION_OPP_ID = "6f987cdc-cb1a-4cc7-81ce-90f958b69d08"
BATCH_PROMPT = 805784
BATCH_COMPLETION = 237443
BATCH_TOTAL = 1043227
BATCH_ASSESSED = 85


@dataclass(slots=True)
class AuditRow:
    opportunity_id: str
    title: str
    organisation: str | None
    source: str | None
    location: str | None
    deadline: str | None
    source_data_sufficiency: str | None
    assessment_status: str
    overall_relevance: str | None
    scope_summary: str | None
    rationale: str | None
    ranking_score: int | None
    ranking_band: str | None
    ranking_status: str | None
    review_disposition: str | None
    review_recorded_at: str | None
    review_timing_vs_v4: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    assessment_id: str
    assessed_at: str


def _disposition_label(value: str | None) -> str:
    return value if value else "UNREVIEWED"


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _review_timing(
    review_at: datetime | None, assessment_at: datetime
) -> str | None:
    if review_at is None:
        return None
    if review_at < assessment_at:
        return "predates_v4"
    if review_at > assessment_at:
        return "postdates_v4"
    return "same_instant"


def _phrase_in_blob(blob: str, phrase: str) -> bool:
    phrase = phrase.strip()
    if not phrase:
        return False
    if " " in phrase:
        return phrase in blob
    return re.search(rf"\b{re.escape(phrase)}\b", blob) is not None


def categorize_weak_fit(title: str, scope: str | None, rationale: str | None) -> str:
    """Bucket by opportunity title only (scope text often mentions land negatively)."""
    blob = title.lower()
    rules: list[tuple[str, tuple[str, ...]]] = [
        (
            "land_cadastre_lis",
            (
                "cadast",
                "land administration",
                "land registry",
                "land information",
                "land tenure",
                "cadastral",
            ),
        ),
        (
            "gis_geospatial_sdi",
            (
                "gis",
                "geospatial",
                "spatial data",
                "postgis",
                "sdi",
                "mapping",
                "cartograph",
            ),
        ),
        ("public_sector_digital", ("digital transformation", "digitalisation", "digitization", "e-government", "egov")),
        ("generic_it_systems", ("information system", "it officer", "ict", "software", "database", "system integrat")),
        ("monitoring_evaluation_research", ("monitoring", "evaluation", "m&e", "research", "data analysis")),
        ("urban_planning", ("urban planning", "urban development", "city planning", "spatial planning")),
        ("infrastructure_engineering", ("civil engineer", "water engineer", "infrastructure", "construction", "wwtp")),
        ("data_statistics", ("statistic", "data scientist", "data manager", "census")),
        ("project_management", ("project manager", "programme manager", "team leader")),
        ("environment_climate_spatial", ("climate", "environmental", "biodiversity", "carbon", "remote sensing")),
        ("land_governance_adjacent", ("land governance", "land policy", "property", "survey")),
    ]
    for label, phrases in rules:
        for phrase in phrases:
            if _phrase_in_blob(blob, phrase):
                return label
    return "other"


def _geo_candidate_flag(title: str, scope: str | None) -> bool:
    blob = title.lower()
    patterns = (
        r"\bcadast",
        r"land administration",
        r"land registration",
        r"land information",
        r"land tenure",
        r"\blis\b",
        r"\bgis\b",
        r"geospatial",
        r"\bsdi\b",
        r"spatial data",
        r"postgis",
        r"interoperab",
        r"land registry",
        r"carte fonci",
    )
    return any(re.search(p, blob) for p in patterns)


def simulate_policies(rows: list[AuditRow]) -> dict[str, Any]:
    def row_disposition(r: AuditRow) -> str:
        return _disposition_label(r.review_disposition)

    def is_unknown(r: AuditRow) -> bool:
        rel = (r.overall_relevance or "").upper()
        return rel in ("UNKNOWN", "INSUFFICIENT_EVIDENCE", "")

    def policy_a_visible(r: AuditRow) -> bool:
        return (r.overall_relevance or "").upper() != "OUT_OF_SCOPE"

    def policy_b_visible(r: AuditRow) -> bool:
        rel = (r.overall_relevance or "").upper()
        return rel in ("STRONG_FIT", "MODERATE_FIT", "WEAK_FIT")

    def policy_c_primary(r: AuditRow) -> bool:
        rel = (r.overall_relevance or "").upper()
        return rel in ("STRONG_FIT", "MODERATE_FIT")

    def policy_c_secondary(r: AuditRow) -> bool:
        return (r.overall_relevance or "").upper() == "WEAK_FIT"

    def summarize(
        name: str,
        primary_fn: Callable[[AuditRow], bool],
        secondary_fn: Optional[Callable[[AuditRow], bool]] = None,
    ) -> dict[str, Any]:
        primary = [r for r in rows if primary_fn(r)]
        secondary = [r for r in rows if secondary_fn(r)] if secondary_fn else []
        hidden_oos = sum(
            1 for r in rows if (r.overall_relevance or "").upper() == "OUT_OF_SCOPE"
        )
        needs_review = sum(1 for r in rows if is_unknown(r))
        dismiss_in_primary = sum(
            1 for r in primary if row_disposition(r) == "DISMISS"
        )
        shortlist_excluded = sum(
            1
            for r in rows
            if row_disposition(r) == "SHORTLIST" and not primary_fn(r)
        )
        geo_fn = _geo_candidate_flag
        false_neg_candidates = [
            r.opportunity_id
            for r in rows
            if (r.overall_relevance or "").upper() == "OUT_OF_SCOPE"
            and geo_fn(r.title, r.scope_summary)
        ]
        return {
            "policy": name,
            "primary_queue_size": len(primary),
            "secondary_queue_size": len(secondary) if secondary_fn else 0,
            "hidden_out_of_scope": hidden_oos
            if name != "A"
            else sum(1 for r in rows if not primary_fn(r)),
            "needs_review_queue": needs_review,
            "dismiss_in_primary": dismiss_in_primary,
            "shortlist_excluded_from_primary": shortlist_excluded,
            "geo_title_scope_oos_candidates": false_neg_candidates[:25],
            "geo_title_scope_oos_candidate_count": len(false_neg_candidates),
        }

    return {
        "policy_A_exclude_oos_only": summarize("A", policy_a_visible),
        "policy_B_exclude_oos_unknown_separate": summarize(
            "B",
            policy_b_visible,
        ),
        "policy_C_primary_strong_moderate": summarize(
            "C",
            policy_c_primary,
            policy_c_secondary,
        ),
    }


def build_report(session) -> dict[str, Any]:
    from jobhunter.application.review.active_strategy import ActiveSearchStrategyResolver
    from jobhunter.application.review.lifecycle import is_actionable_lifecycle
    from jobhunter.application.review.production_selection import select_production_ranking
    from jobhunter.application.review.source_links import pick_primary_source_link
    from jobhunter.domain.assessment_enums import PROFILE_ASSESSMENT_SCHEMA_VERSION
    from jobhunter.domain.enums import EligibilityStatus
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

    if PROFILE_ASSESSMENT_SCHEMA_VERSION != V4_SCHEMA:
        raise RuntimeError(
            f"Expected code schema {V4_SCHEMA}, got {PROFILE_ASSESSMENT_SCHEMA_VERSION}"
        )

    ctx = ActiveSearchStrategyResolver(session).resolve()
    revision_id = ctx.revision_id

    opps = OpportunityRepository(session).list_all()
    job_sources = JobSourceRepository(session)
    opp_sources = OpportunitySourceRepository(session)
    assessments_repo = OpportunityProfileAssessmentRepository(session)
    rankings_repo = OpportunityRankingRepository(session)
    reviews_repo = OpportunityReviewRecordRepository(session)

    all_v4_rows: list = []
    for opp in opps:
        for a in assessments_repo.list_for_opportunity(opp.id):
            if (
                a.search_strategy_revision_id == revision_id
                and a.is_successful
                and a.model_provider != "fake"
                and a.prompt_schema_version == V4_SCHEMA
            ):
                all_v4_rows.append(a)

    def current_v4(opp_id: str):
        return assessments_repo.get_latest_success_for_revision(
            opp_id, revision_id, allow_fake=False
        )

    actionable = [o for o in opps if is_actionable_lifecycle(o.lifecycle_status)]
    actionable_eligible = [
        o
        for o in actionable
        if o.eligibility_status is EligibilityStatus.ELIGIBLE
    ]

    audit_rows: list[AuditRow] = []
    population_v4_current = 0
    missing_v4 = 0

    assessment_by_id = {a.id: a for a in all_v4_rows if a.id}

    for opp in actionable_eligible:
        assessment = current_v4(opp.id)
        if assessment is None or assessment.prompt_schema_version != V4_SCHEMA:
            missing_v4 += 1
            continue
        population_v4_current += 1

        result = assessment.result or {}
        prof = result.get("professional_relevance") or {}
        links = opp_sources.list_for_opportunity(opp.id)
        primary = pick_primary_source_link(links, job_sources)

        rankings = rankings_repo.list_for_opportunity_and_revision(opp.id, revision_id)
        rankings_sorted = sorted(rankings, key=lambda r: r.ranked_at, reverse=True)
        ranking = select_production_ranking(
            rankings_sorted, assessment_by_id, allow_fake=False
        )

        review = reviews_repo.get_latest_for_opportunity(opp.id)
        scope = str(prof.get("scope_summary") or "")[:800] or None
        rationale = str(result.get("rationale") or "")[:800] or None

        audit_rows.append(
            AuditRow(
                opportunity_id=opp.id,
                title=opp.title,
                organisation=opp.organisation,
                source=primary.source_name if primary else None,
                location=opp.location,
                deadline=_iso(opp.deadline),
                source_data_sufficiency=str(
                    result.get("source_data_sufficiency") or ""
                )
                or None,
                assessment_status=assessment.status.value,
                overall_relevance=str(result.get("overall_relevance") or "") or None,
                scope_summary=scope,
                rationale=rationale,
                ranking_score=ranking.internal_sort_score if ranking else None,
                ranking_band=ranking.priority_band.value
                if ranking and ranking.priority_band
                else None,
                ranking_status=ranking.status.value if ranking else None,
                review_disposition=review.disposition.value if review else None,
                review_recorded_at=_iso(review.recorded_at) if review else None,
                review_timing_vs_v4=_review_timing(
                    review.recorded_at if review else None,
                    assessment.assessed_at,
                ),
                prompt_tokens=assessment.prompt_tokens,
                completion_tokens=assessment.completion_tokens,
                total_tokens=assessment.total_tokens,
                assessment_id=assessment.id,
                assessed_at=_iso(assessment.assessed_at) or "",
            )
        )

    relevance_counts = Counter(
        (r.overall_relevance or "NONE") for r in audit_rows
    )
    status_counts = Counter(r.assessment_status for r in audit_rows)
    band_counts = Counter(
        (r.ranking_band or "NONE")
        for r in audit_rows
        if r.ranking_status == "RANKED"
    )
    review_counts = Counter(
        _disposition_label(r.review_disposition) for r in audit_rows
    )

    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in audit_rows:
        rel = (r.overall_relevance or "NONE").upper()
        disp = _disposition_label(r.review_disposition)
        matrix[rel][disp] += 1

    dismiss_rows = [r for r in audit_rows if r.review_disposition == "DISMISS"]
    dismiss_by_rel = Counter((r.overall_relevance or "NONE") for r in dismiss_rows)

    weak_rows = [r for r in audit_rows if r.overall_relevance == "WEAK_FIT"]
    weak_categories: dict[str, list[AuditRow]] = defaultdict(list)
    for r in weak_rows:
        weak_categories[categorize_weak_fit(r.title, r.scope_summary, r.rationale)].append(
            r
        )

    weak_analysis = {}
    for cat, items in sorted(weak_categories.items(), key=lambda x: -len(x[1])):
        weak_analysis[cat] = {
            "count": len(items),
            "example_titles": [i.title[:100] for i in items[:5]],
            "review_distribution": dict(
                Counter(_disposition_label(i.review_disposition) for i in items)
            ),
        }

    strong_mod = [
        r
        for r in audit_rows
        if r.overall_relevance in ("STRONG_FIT", "MODERATE_FIT")
    ]
    strong_mod_list = [
        {
            "id": r.opportunity_id,
            "title": r.title[:120],
            "organisation": r.organisation,
            "source": r.source,
            "relevance": r.overall_relevance,
            "ranking_band": r.ranking_band,
            "ranking_score": r.ranking_score,
            "disposition": _disposition_label(r.review_disposition),
            "scope_summary": (r.scope_summary or "")[:200],
            "geo_keyword_candidate": _geo_candidate_flag(r.title, r.scope_summary),
        }
        for r in sorted(strong_mod, key=lambda x: (x.overall_relevance or "", x.title))
    ]

    oos_rows = [r for r in audit_rows if r.overall_relevance == "OUT_OF_SCOPE"]
    oos_geo_candidates = [
        {
            "id": r.opportunity_id,
            "title": r.title[:120],
            "disposition": _disposition_label(r.review_disposition),
            "scope_summary": (r.scope_summary or "")[:200],
        }
        for r in oos_rows
        if _geo_candidate_flag(r.title, r.scope_summary)
    ]

    rel_x_band: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in audit_rows:
        if r.ranking_status != "RANKED":
            continue
        rel_x_band[(r.overall_relevance or "NONE")][r.ranking_band or "NONE"] += 1

    tokens_prompt = [a.prompt_tokens for a in all_v4_rows if a.prompt_tokens is not None]
    tokens_completion = [
        a.completion_tokens for a in all_v4_rows if a.completion_tokens is not None
    ]
    tokens_total = [a.total_tokens for a in all_v4_rows if a.total_tokens is not None]

    def token_stats(vals: list[int]) -> dict[str, Any]:
        if not vals:
            return {}
        ordered = sorted(vals)
        p90 = ordered[int(len(ordered) * 0.9) - 1] if len(ordered) >= 10 else max(vals)
        return {
            "count": len(vals),
            "sum": sum(vals),
            "mean": int(statistics.mean(vals)),
            "median": int(statistics.median(vals)),
            "p90": p90,
            "min": min(vals),
            "max": max(vals),
        }

    cal_v4 = [
        a
        for a in assessments_repo.list_for_opportunity(CALIBRATION_OPP_ID)
        if a.prompt_schema_version == V4_SCHEMA and a.is_successful
    ]
    cal_v4_sorted = sorted(cal_v4, key=lambda a: a.assessed_at)

    token_reconciliation = {
        "all_v4_success_rows_on_revision": len(all_v4_rows),
        "unique_opportunities_with_any_v4_row": len({a.opportunity_id for a in all_v4_rows}),
        "persisted_prompt_sum": sum(tokens_prompt),
        "persisted_completion_sum": sum(tokens_completion),
        "persisted_total_sum": sum(tokens_total),
        "batch_reported": {
            "assessed": BATCH_ASSESSED,
            "prompt": BATCH_PROMPT,
            "completion": BATCH_COMPLETION,
            "total": BATCH_TOTAL,
        },
        "calibration_opportunity_id": CALIBRATION_OPP_ID,
        "calibration_v4_assessment_count": len(cal_v4_sorted),
        "calibration_v4_assessments": [
            {
                "id": a.id,
                "assessed_at": _iso(a.assessed_at),
                "overall": (a.result or {}).get("overall_relevance"),
                "prompt_tokens": a.prompt_tokens,
                "total_tokens": a.total_tokens,
            }
            for a in cal_v4_sorted
        ],
        "note": (
            "Batch totals are operator-reported for 85 calls. Persisted sums include "
            "all v4 rows on the active revision (including a second v4 row for "
            "calibration opportunity C if force-reassessed after the batch)."
        ),
    }

    unique_v4_opps = {a.opportunity_id for a in all_v4_rows}
    actionable_eligible_ids = {o.id for o in actionable_eligible}

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "revision_id": revision_id,
        "schema_version": V4_SCHEMA,
        "population": {
            "total_opportunities": len(opps),
            "actionable": len(actionable),
            "actionable_eligible": len(actionable_eligible),
            "current_v4_on_latest_success": population_v4_current,
            "actionable_eligible_missing_v4": missing_v4,
            "unique_opportunities_with_v4_row": len(unique_v4_opps),
            "v4_rows_total_on_revision": len(all_v4_rows),
            "actionable_eligible_without_any_v4": len(
                actionable_eligible_ids - unique_v4_opps
            ),
        },
        "v4_assessment_status_counts": dict(status_counts),
        "v4_overall_relevance_counts": dict(relevance_counts),
        "ranking_band_counts_ranked": dict(band_counts),
        "latest_human_review_counts": dict(review_counts),
        "relevance_x_disposition": {k: dict(v) for k, v in matrix.items()},
        "relevance_percentages": {
            k: round(100.0 * v / len(audit_rows), 1) if audit_rows else 0
            for k, v in relevance_counts.items()
        },
        "dismiss_analysis": {
            "total_dismiss": len(dismiss_rows),
            "by_overall_relevance": dict(dismiss_by_rel),
            "dismiss_out_of_scope": [
                {"id": r.opportunity_id, "title": r.title[:100]}
                for r in dismiss_rows
                if r.overall_relevance == "OUT_OF_SCOPE"
            ],
            "dismiss_weak_fit": [
                {
                    "id": r.opportunity_id,
                    "title": r.title[:100],
                    "category": categorize_weak_fit(
                        r.title, r.scope_summary, r.rationale
                    ),
                    "scope_summary": (r.scope_summary or "")[:180],
                }
                for r in dismiss_rows
                if r.overall_relevance == "WEAK_FIT"
            ],
            "dismiss_moderate_fit": [
                {
                    "id": r.opportunity_id,
                    "title": r.title[:100],
                    "scope_summary": (r.scope_summary or "")[:180],
                    "rationale": (r.rationale or "")[:180],
                }
                for r in dismiss_rows
                if r.overall_relevance == "MODERATE_FIT"
            ],
            "dismiss_strong_fit": [
                {
                    "id": r.opportunity_id,
                    "title": r.title[:100],
                    "scope_summary": (r.scope_summary or "")[:180],
                    "rationale": (r.rationale or "")[:180],
                }
                for r in dismiss_rows
                if r.overall_relevance == "STRONG_FIT"
            ],
        },
        "weak_fit_analysis": weak_analysis,
        "strong_moderate_inspection": strong_mod_list,
        "out_of_scope_summary": {
            "count": len(oos_rows),
            "example_titles": [r.title[:100] for r in oos_rows[:15]],
            "review_distribution": dict(
                Counter(_disposition_label(r.review_disposition) for r in oos_rows)
            ),
            "geo_keyword_candidates": oos_geo_candidates,
        },
        "overall_relevance_x_ranking_band": {k: dict(v) for k, v in rel_x_band.items()},
        "queue_policy_simulation": simulate_policies(audit_rows),
        "token_statistics": {
            "prompt_tokens": token_stats(tokens_prompt),
            "completion_tokens": token_stats(tokens_completion),
            "total_tokens": token_stats(tokens_total),
        },
        "token_reconciliation": token_reconciliation,
        "audit_dataset": [asdict(r) for r in audit_rows],
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    pop = report["population"]
    rel = report["v4_overall_relevance_counts"]
    lines = [
        "# Phase 17G-2A — Post-reassessment decision-quality audit",
        "",
        "## 1. Executive summary",
        "",
        f"Active revision `{report['revision_id']}`. "
        f"**{pop['current_v4_on_latest_success']}** eligible+actionable opportunities "
        f"have a current **{V4_SCHEMA}** assessment. "
        f"Relevance distribution is dominated by **WEAK_FIT** ({rel.get('WEAK_FIT', 0)}), "
        f"with **OUT_OF_SCOPE** ({rel.get('OUT_OF_SCOPE', 0)}) aligning well with many "
        f"prior **DISMISS** decisions. **STRONG_FIT** / **MODERATE_FIT** clusters look "
        f"plausible for land/cadastre and adjacent digital roles; gate design should "
        f"treat **WEAK_FIT** as a first-class queue segment, not hide it with OUT_OF_SCOPE.",
        "",
        "## 2. Population / reassessment reconciliation",
        "",
        f"- Total opportunities: **{pop['total_opportunities']}**",
        f"- Actionable: **{pop['actionable']}**",
        f"- Actionable + ELIGIBLE: **{pop['actionable_eligible']}**",
        f"- Current v4 (latest success): **{pop['current_v4_on_latest_success']}**",
        f"- Missing v4 on latest success: **{pop['actionable_eligible_missing_v4']}**",
        f"- Total v4 assessment rows on revision: **{pop['v4_rows_total_on_revision']}**",
        f"- Unique opps with any v4 row: **{pop['unique_opportunities_with_v4_row']}**",
        "",
        report["token_reconciliation"]["note"],
        "",
        "## 3. Relevance distribution",
        "",
        "```json",
        json.dumps(rel, indent=2),
        "```",
        "",
        "## 4. Relevance × human review",
        "",
        "```json",
        json.dumps(report["relevance_x_disposition"], indent=2),
        "```",
        "",
        "## 5. DISMISS disagreement analysis",
        "",
        f"Total DISMISS in audit set: **{report['dismiss_analysis']['total_dismiss']}**",
        "",
        "```json",
        json.dumps(report["dismiss_analysis"]["by_overall_relevance"], indent=2),
        "```",
        "",
        "## 6. WEAK_FIT analysis",
        "",
        "```json",
        json.dumps(report["weak_fit_analysis"], indent=2),
        "```",
        "",
        "## 7. STRONG / MODERATE inspection",
        "",
        f"See `strong_moderate_inspection` in JSON ({len(report['strong_moderate_inspection'])} rows).",
        "",
        "## 8. OUT_OF_SCOPE false-negative candidates",
        "",
        f"Keyword-flagged candidates for manual review: "
        f"**{len(report['out_of_scope_summary']['geo_keyword_candidates'])}** "
        f"(see JSON; not automatic ground truth).",
        "",
        "## 9. Relevance × ranking",
        "",
        "```json",
        json.dumps(report["overall_relevance_x_ranking_band"], indent=2),
        "```",
        "",
        "## 10. Queue policy simulation",
        "",
        "```json",
        json.dumps(report["queue_policy_simulation"], indent=2),
        "```",
        "",
        "## 11. Token statistics",
        "",
        "```json",
        json.dumps(report["token_statistics"], indent=2),
        "```",
        "",
        "## 12. Recommended 17G-2B design",
        "",
        "See report section 12 in the Cursor deliverable (derived from this data).",
        "",
        "## 13. Risks / safeguards",
        "",
        "- Do not hide WEAK_FIT solely because of DISMISS history.",
        "- OUT_OF_SCOPE + geo keyword hits require manual false-negative review before tightening gate.",
        "- UNKNOWN / INSUFFICIENT_EVIDENCE → needs-review queue, not default.",
        "",
        "## 14. Reproduce",
        "",
        "```bash",
        "python scripts/analyze_v4_decision_quality.py",
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    bootstrap_repo()
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )

    root = Path(__file__).resolve().parents[1]
    settings = get_settings()
    settings.require_database_url()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            report = build_report(session)
    finally:
        engine.dispose()

    json_path = root / "docs" / "analysis" / "phase-17g-2a-decision-quality-audit.json"
    md_path = root / "docs" / "analysis" / "phase-17g-2a-decision-quality-audit.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, md_path)

    print(f"wrote {json_path.relative_to(root)}")
    print(f"wrote {md_path.relative_to(root)}")
    print("population", json.dumps(report["population"], indent=2))
    print("relevance", json.dumps(report["v4_overall_relevance_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
