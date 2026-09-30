"""17G-2B-pre: review UNREVIEWED WEAK_FIT + MODERATE_FIT (read-only).

Uses v4 audit data from DB via analyze_v4_decision_quality.build_report.
Run: python scripts/analyze_unreviewed_weak_moderate_pre.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from _script_bootstrap import bootstrap_repo

# Analysis-only buckets (not persisted).
CORE_TARGET = "CORE_TARGET"
ADJACENT_PLAUSIBLE = "ADJACENT_PLAUSIBLE"
PROBABLY_NOT_FOR_ME = "PROBABLY_NOT_FOR_ME"
INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"

TARGET_PHRASES = (
    "cadast",
    "land administration",
    "land registry",
    "land information",
    "land registration",
    "geospatial",
    "spatial data",
    "postgis",
    "gis",
    " sdi",
    "nsdi",
    "interoperab",
    "lis implementation",
    "carte fonci",
    "egib",
    "systematic land",
)


def _phrase_in_blob(blob: str, phrase: str) -> bool:
    phrase = phrase.strip()
    if " " in phrase:
        return phrase in blob
    return re.search(rf"\b{re.escape(phrase)}\b", blob) is not None


def classify_analysis_bucket(row: dict[str, Any]) -> str:
    """Heuristic analysis bucket from title + sufficiency + scope (audit-only)."""
    title_l = (row.get("title") or "").lower()
    scope_l = (row.get("scope_summary") or "").lower()
    suff = row.get("source_data_sufficiency") or ""
    blob = f"{title_l} {scope_l}"

    # Opportunity title only for geo phrases — scope_summary repeats profile GIS/LIS text.
    for phrase in TARGET_PHRASES:
        if not _phrase_in_blob(title_l, phrase.strip()):
            continue
        if any(
            x in title_l
            for x in (
                "civil engineer",
                "scrum",
                "meal",
                "agricultural officer",
                "sanitation",
                "hsse",
                "administrative officer",
                "supervision of building",
            )
        ):
            break
        core_phrases = (
            "cadast",
            "land administration",
            "land registry",
            "land information",
            "systematic land",
            "egib",
            "land registration",
        )
        return CORE_TARGET if phrase in core_phrases else ADJACENT_PLAUSIBLE

    if suff == "LIST_SUMMARY_ONLY":
        if any(
            k in title_l
            for k in ("data", "information system", "digital", "gis", "geospatial")
        ):
            return INSUFFICIENT_INFORMATION
        return INSUFFICIENT_INFORMATION

    if any(
        k in title_l
        for k in (
            "topograph",
            "géomètre",
            "geometer",
            "survey",
            "geomat",
        )
    ):
        return ADJACENT_PLAUSIBLE

    if any(
        k in title_l
        for k in (
            "digital",
            "digitalisation",
            "digitalization",
            "information system",
            "it and",
            "ict",
            "data and information",
            "ciência de dados",
            "data science",
            "scrum",
            "platform",
            "modernización digital",
        )
    ):
        if "scrum" in title_l:
            return PROBABLY_NOT_FOR_ME
        if "data science" in title_l or "ciência de dados" in title_l:
            return ADJACENT_PLAUSIBLE
        return ADJACENT_PLAUSIBLE

    if any(
        k in title_l
        for k in (
            "administrative",
            "administration specialist",
            "meal",
            "monitoring evaluation",
            "research and data",
            "agricultural",
            "coordinador",
            "programme management",
            "partnership",
            "alianzas",
            "supervision of building",
            "construction",
        )
    ):
        if "coordinador" in title_l or "programme management" in title_l:
            return INSUFFICIENT_INFORMATION
        return PROBABLY_NOT_FOR_ME

    if "innovation" in title_l and "agriculture" in title_l:
        return ADJACENT_PLAUSIBLE

    return PROBABLY_NOT_FOR_ME


def why_relevance_label(row: dict[str, Any]) -> str:
    rat = (row.get("rationale") or "")[:300]
    if rat:
        return rat.split(".")[0].strip() + "."
    scope = (row.get("scope_summary") or "")[:200]
    return scope or "See scope_summary in audit row."


def simulate_policies(all_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def disp(r: dict) -> str:
        return r.get("review_disposition") or "UNREVIEWED"

    def rel(r: dict) -> str:
        return (r.get("overall_relevance") or "").upper()

    def metrics(primary: list[dict], secondary: list[dict], hidden_weak: int) -> dict:
        return {
            "primary_default_queue": len(primary),
            "secondary_or_hidden_weak": len(secondary) + hidden_weak,
            "secondary_queue": len(secondary),
            "hidden_weak_only": hidden_weak,
            "dismiss_in_primary": sum(1 for r in primary if disp(r) == "DISMISS"),
            "unreviewed_in_primary": sum(1 for r in primary if disp(r) == "UNREVIEWED"),
            "shortlist_excluded_from_primary": sum(
                1 for r in all_rows if disp(r) == "SHORTLIST" and r not in primary
            ),
            "core_target_unreviewed_in_primary": sum(
                1
                for r in primary
                if disp(r) == "UNREVIEWED"
                and classify_analysis_bucket(r) == CORE_TARGET
            ),
            "adjacent_unreviewed_excluded_from_primary": sum(
                1
                for r in all_rows
                if disp(r) == "UNREVIEWED"
                and r not in primary
                and classify_analysis_bucket(r)
                in (CORE_TARGET, ADJACENT_PLAUSIBLE)
            ),
        }

    p1 = [r for r in all_rows if rel(r) != "OUT_OF_SCOPE"]
    p2_primary = [r for r in all_rows if rel(r) in ("STRONG_FIT", "MODERATE_FIT")]
    p2_secondary = [r for r in all_rows if rel(r) == "WEAK_FIT"]
    p3_primary = p2_primary
    p3_hidden_weak = len(p2_secondary)

    return {
        "policy_1_strong_moderate_weak_visible": metrics(
            p1, [], 0
        ),
        "policy_2_primary_strong_moderate_secondary_weak": metrics(
            p2_primary, p2_secondary, 0
        ),
        "policy_3_weak_hidden_filter": metrics(p3_primary, [], p3_hidden_weak),
        "hidden_out_of_scope_all_policies": sum(
            1 for r in all_rows if rel(r) == "OUT_OF_SCOPE"
        ),
    }


def main() -> int:
    bootstrap_repo()
    root = Path(__file__).resolve().parents[1]
    from jobhunter.ai.factory import resolve_assessment_model
    from jobhunter.infrastructure.config import get_settings
    from jobhunter.infrastructure.persistence.database import (
        create_engine_from_settings,
        create_session_factory,
        session_scope,
    )
    sys.path.insert(0, str(root / "scripts"))
    from analyze_v4_decision_quality import build_report

    settings = get_settings()
    settings.require_database_url()
    model = resolve_assessment_model(settings, "openai")
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)

    try:
        with session_scope(session_factory) as session:
            report = build_report(session)
    finally:
        engine.dispose()

    all_rows = report["audit_dataset"]
    focus = [
        r
        for r in all_rows
        if not r.get("review_disposition")
        and r.get("overall_relevance") in ("WEAK_FIT", "MODERATE_FIT")
    ]
    if len(focus) != 15:
        print(
            f"Expected 15 UNREVIEWED WEAK/MODERATE rows, found {len(focus)}",
            file=sys.stderr,
        )

    enriched = []
    for r in focus:
        bucket = classify_analysis_bucket(r)
        enriched.append(
            {
                **r,
                "analysis_bucket": bucket,
                "why_relevance": why_relevance_label(r),
            }
        )

    cross = defaultdict(lambda: defaultdict(int))
    for r in enriched:
        cross[r["overall_relevance"]][r["analysis_bucket"]] += 1

    out = {
        "phase": "17G-2B-pre",
        "cases": enriched,
        "cross_tab_relevance_x_analysis_bucket": {
            k: dict(v) for k, v in cross.items()
        },
        "policy_simulation_86_eligible_actionable": simulate_policies(all_rows),
    }

    json_path = root / "docs/analysis/phase-17g-2b-pre-unreviewed-weak-moderate.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = root / "docs/analysis/phase-17g-2b-pre-unreviewed-weak-moderate.md"
    md_path.write_text(_render_md(enriched, cross, out["policy_simulation_86_eligible_actionable"]), encoding="utf-8")

    print(f"wrote {json_path.relative_to(root)}")
    print(f"wrote {md_path.relative_to(root)}")
    return 0


def _render_md(enriched, cross, policies) -> str:
    lines = [
        "# 17G-2B-pre — UNREVIEWED WEAK_FIT / MODERATE_FIT review",
        "",
        "## A. Case table (15)",
        "",
        "| UUID | Rel | Bucket | Band | Sufficiency | Title |",
        "|------|-----|--------|------|-------------|-------|",
    ]
    for r in sorted(enriched, key=lambda x: (x["overall_relevance"], x["title"])):
        lines.append(
            f"| `{r['opportunity_id']}` | {r['overall_relevance']} | {r['analysis_bucket']} | "
            f"{r.get('ranking_band') or '—'} | {r.get('source_data_sufficiency')} | "
            f"{r['title'][:60].replace('|', '/')} |"
        )
    lines.extend(["", "## B. Cross-tab (relevance × analysis bucket)", "", "```json"])
    lines.append(json.dumps({k: dict(v) for k, v in cross.items()}, indent=2))
    lines.extend(["```", "", "## E. Policy simulation (86 v4 eligible+actionable)", "", "```json"])
    lines.append(json.dumps(policies, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Case detail")
    lines.append("")
    for r in sorted(enriched, key=lambda x: (x["overall_relevance"], x["title"])):
        lines.append(f"### {r['title'][:80]}")
        lines.append(f"- **UUID:** `{r['opportunity_id']}`")
        lines.append(f"- **Organisation:** {r.get('organisation') or '—'}")
        lines.append(f"- **Source:** {r.get('source')}")
        lines.append(f"- **Relevance / bucket:** {r['overall_relevance']} / {r['analysis_bucket']}")
        lines.append(
            f"- **Ranking:** {r.get('ranking_status')} score={r.get('ranking_score')} band={r.get('ranking_band')}"
        )
        lines.append(f"- **Why {r['overall_relevance']}:** {r['why_relevance']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
