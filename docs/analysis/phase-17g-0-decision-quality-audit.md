# Phase 17G-0 — Opportunity decision-quality audit (investigation)

**Date:** 2026-09-29  
**Scope:** Read-only analysis of production PostgreSQL (105 opportunities).  
**No production semantics changed** in this phase.

Re-run data export:

```bash
python scripts/analyze_decision_quality_audit.py
```

Raw aggregates: `docs/analysis/phase-17g-0-audit-data.json`.

---

## 1. Current decision architecture

```text
Source scan / connector
    → Raw opportunity → Normalise → Persist opportunity (+ sources)
    → EligibilityFilterService (lifecycle + configured exclusions + HARD_CONSTRAINT criteria)
    → Opportunity lifecycle on opportunity row (ELIGIBLE / INELIGIBLE / REVIEW_REQUIRED / UNKNOWN)
    → (Automation) Profile assessment (OpenAI JSON) per active search strategy revision
    → OpportunityRankingCalculator (ranking_v1, deterministic score → band)
    → OpportunityReviewQueryService.list_queue (UI default filters)
    → Human review (append-only OpportunityReviewRecord)
```

**Professional / domain relevance today**

| Stage | Role |
|--------|------|
| **Acquisition / search** | Recall-oriented; themes and terms cast a wide net (by design). |
| **Hard eligibility** | “Can I apply?” — deadline, junior/internship, nationality/residency-style exclusions, configured hard constraints. **No professional-domain gate.** |
| **Assessment** | **Primary** semantic relevance: `overall_relevance`, `professional_relevance`, service/theme alignments, evidence sections. |
| **Ranking** | Maps assessment signals to **priority band** (HIGH / MEDIUM / LOW / REVIEW); does not drop opportunities from the queue. |
| **Review queue** | Default: actionable lifecycle + **ELIGIBLE** only; includes all ranked bands unless filtered. **No filter on overall_relevance or OUT_OF_SCOPE.** |

There is **no separate “Professional Relevance” stage** between eligibility and assessment. `OUT_OF_SCOPE` exists in the assessment enum and ranking points (100 pts → usually **LOW**), but nothing prevents those rows from appearing in the default queue.

---

## 2. What LOW means today

From `ranking_config_v1` + `_resolve_priority_band`:

- Internal score from assessment (`overall_relevance` dominates: STRONG_FIT 400 … OUT_OF_SCOPE 100 … UNKNOWN 50) plus service/theme alignment, eligibility uncertainty penalties, source sufficiency, interpreted eligibility concerns.
- **HIGH** if score ≥ 370 (and eligibility not forcing REVIEW band).
- **MEDIUM** if score ≥ 250.
- **LOW** otherwise (for rankable, ELIGIBLE opportunities).
- **REVIEW** band if eligibility is `REVIEW_REQUIRED` or `UNKNOWN` (eligibility uncertainty), regardless of score.

**LOW is therefore “low computed priority”, not “professionally relevant but weak fit”.**  
A clear domain mismatch that still receives `overall_relevance=UNKNOWN` (50 pts) or `OUT_OF_SCOPE` (100 pts) is typically **LOW** but remains in the default queue alongside genuinely adjacent weak-fit roles.

---

## 3. Production snapshot (active strategy revision)

| Metric | Count |
|--------|------:|
| Total opportunities | 105 |
| Default Opportunities queue (`ELIGIBLE`, actionable lifecycle) | 86 |
| Eligible | 86 |
| Ineligible | 13 |
| Review required (eligibility) | 6 |
| Ranked — LOW band | 60 |
| Ranked — REVIEW band | 4 |
| Unranked | 16 |
| No production assessment | 40 |
| Production assessment `overall_relevance` | **65 × UNKNOWN** (no STRONG/MODERATE/WEAK/OUT_OF_SCOPE in DB) |
| Human review DISMISS | 58 |
| Human review SHORTLIST / INVESTIGATE | **0** |

### Band × disposition (ranked opportunities only)

| | DISMISS | UNREVIEWED | SHORTLIST |
|--|--------:|-----------:|----------:|
| **LOW** | **50** | **10** | 0 |
| **REVIEW** | 0 | 4 | 0 |
| **MEDIUM** | 0 | — | 0 |
| **HIGH** | 0 | — | 0 |

---

## 4. Why obvious mismatches reach LOW + review

### Representative false positives (LOW + DISMISS, assessment-backed)

Production samples show a consistent pattern:

- Titles: HSSE/Safeguard Officer, Civil Engineer, Climate Resilience/Environmental Specialist, Gender and Social Inclusion Specialist, evaluation assignments, UNDP finance/HR/admin roles, MCA programme managers, etc.
- **`overall_relevance`: UNKNOWN** (not OUT_OF_SCOPE).
- **`professional_relevance.scope_summary`**: empty; domain tags empty.
- **`rationale`**: often empty in stored JSON.
- **`source_data_sufficiency`**: often ADEQUATE (DevelopmentAid) or PARTIAL (UNDP) — so the model is **not** deferring for list-only data.
- **Internal scores**: typically 25–50 → **LOW** band.
- **Eligibility**: ELIGIBLE — hard rules did not exclude.

**Interpretation:** The pipeline **allowed and ranked** these because (1) search/acquisition recalled them, (2) eligibility passed, (3) assessment did **not** classify them as OUT_OF_SCOPE, (4) ranking correctly treated UNKNOWN as low score, (5) the queue does not hide LOW or UNKNOWN relevance.

### LOW + unreviewed (10 ranked)

Diagnostic heuristic (analysis-only): all 10 bucketed as **insufficient_source_data / UNKNOWN relevance** — same underlying assessment sparsity, not a separate queue bug.

### Positive controls (SHORTLIST)

**None in production** at audit time — cannot empirically validate SHORTLIST characteristics from live data. Use **Home HIGH preview design intent** and assessment schema (service/theme alignment, STRONG_FIT / MODERATE_FIT) as the target profile for a future gate’s “must not block” set.

### Geo-relevant title candidates

See `geo_relevant_title_candidates` in JSON export — use for **false-negative** review before any keyword gate. Any role with land/GIS/cadastre in the title but `UNKNOWN` assessment needs **assessment fix** more than keyword exclusion.

---

## 5. Root-cause synthesis

| Factor | Contribution |
|--------|----------------|
| **Acquisition breadth** | **High** — multi-source (FAO, UNDP, DevelopmentAid, etc.) with wide recall. |
| **Hard eligibility intentionally broad** | **High** — excludes structural ineligibility, not profession mismatch. |
| **Assessment prompt / model output** | **Critical** — production assessments overwhelmingly **UNKNOWN** with empty professional_relevance and rationale; relevance signal **not operationalised** in stored results. |
| **Ranking** | **Behaves as designed** given inputs; collapses unknown fit to LOW, does not filter. |
| **Review queue filtering** | **No relevance filter** — all eligible actionable ranked/unranked rows visible (86 in queue). |
| **Source data insufficiency** | **Mixed** — some FAO list-only (score 25); many DevelopmentAid ADEQUATE mismatches still UNKNOWN. |

**Primary issue:** Professional relevance is **defined** in assessment but **not effectively produced or enforced** before human review. LOW mixes (a) “unknown / unassessed fit” and (b) “human-dismissed obvious mismatch” without a **professionally irrelevant** lifecycle or queue exclusion.

---

## 6. Proposed 17G direction (conceptual — not implemented)

### Pipeline

```text
Acquisition → Hard Eligibility → Professional Relevance → Assessment → Ranking → Human Review
```

- **Hard eligibility:** unchanged semantics (“can I apply?”).
- **Professional relevance (new):** “Is this in-domain enough to spend assessment/review attention?”  
  - Candidates: `PROFESSIONALLY_IRRELEVANT` | `BORDERLINE` | `IN_DOMAIN` | `INSUFFICIENT_EVIDENCE`.
- **LOW band (future):** reserve for **IN_DOMAIN** with weak fit (WEAK_FIT / low score), not unrelated professions.

### Recommended mechanism: **hybrid**

1. **Deterministic pre-filter (narrow):** high-confidence exclusions (e.g. explicit HR-only, pure audit/evaluation TOR patterns) — **optional, conservative**.
2. **AI classification:** lightweight pass or **fix existing assessment** to reliably emit `overall_relevance` + `professional_relevance.scope_summary` + explicit OUT_OF_SCOPE when appropriate.
3. **Do not rely on ranking alone** to remove queue noise.

Justification: production data shows **keyword-only gates risk false negatives** on interdisciplinary postings (e.g. “digital solutions”, MCA infrastructure IT, research/data with spatial components) while current failure mode is **under-classification (UNKNOWN)**, not over-aggressive OUT_OF_SCOPE.

### Suggested statuses / UX

| Status | Default queue | Audit view |
|--------|---------------|------------|
| PROFESSIONALLY_IRRELEVANT | Hidden | Visible with reason + source excerpt |
| BORDERLINE / INSUFFICIENT_EVIDENCE | Optional “review” bucket | Full text |
| IN_DOMAIN | Unchanged | — |

### Estimated impact (analysis-only gate on current queue)

From heuristic in audit script (UNKNOWN/INSUFFICIENT → `NEEDS_EVIDENCE_OR_REVIEW`):

- **86** default-queue rows → **86** flagged `NEEDS_EVIDENCE_OR_REVIEW` under current assessment quality (i.e. gate would not shrink queue until assessments discriminate).

Once assessments emit OUT_OF_SCOPE reliably, a gate on `OUT_OF_SCOPE` + empty geo/LIS service alignment would move a **large share of current LOW+DISMISS** titles out of the default queue without waiting for human dismiss.

---

## 7. False-negative risks (naive keyword gate)

Preserve and manually review titles matching: land administration, cadastre, LIS, GIS implementation, spatial data infrastructure, registry digitization, geospatial **database/developer**, interoperability — including when embedded in wider programmes (MCA, World Bank, EU).  
**Reject** using title-only blocks on: “environment”, “climate”, “gender”, “evaluation”, “research” **without** reading TOR — many are irrelevant, but some hybrid posts are not.

---

## 8. Follow-up before implementation (17G)

1. **Investigate why OpenAI assessments return UNKNOWN with empty rationale** (prompt, model, validation, or batch input).  
2. Re-assess a stratified sample after assessment quality fix.  
3. Design professional relevance gate using **assessment OUT_OF_SCOPE + structured professional_relevance**, not LOW band alone.  
4. Add SHORTLIST/INVESTIGATE examples in production to calibrate positive controls.

---

## Files

| File | Purpose |
|------|---------|
| `scripts/analyze_decision_quality_audit.py` | Read-only audit exporter |
| `docs/analysis/phase-17g-0-audit-data.json` | Generated aggregates and samples |
| `docs/analysis/phase-17g-0-decision-quality-audit.md` | This report |

**Tests:** None added (investigation-only).  
**Alembic:** No migration (`20260928_0014` unchanged).  
**Working tree:** Analysis script + `docs/analysis/*` (commit optional for record-keeping).
