# Phase 17G-2A — Post-reassessment decision-quality audit

## 1. Executive summary

Active revision `5d329baf-d79d-5cd1-ad52-751b373bf0ab`. **86** eligible+actionable opportunities have a current **profile_assessment_v4** assessment. Relevance distribution is dominated by **WEAK_FIT** (45), with **OUT_OF_SCOPE** (24) aligning well with many prior **DISMISS** decisions. **STRONG_FIT** / **MODERATE_FIT** clusters look plausible for land/cadastre and adjacent digital roles; gate design should treat **WEAK_FIT** as a first-class queue segment, not hide it with OUT_OF_SCOPE.

## 2. Population / reassessment reconciliation

- Total opportunities: **105**
- Actionable: **95**
- Actionable + ELIGIBLE: **86**
- Current v4 (latest success): **86**
- Missing v4 on latest success: **0**
- Total v4 assessment rows on revision: **86**
- Unique opps with any v4 row: **86**

Batch totals are operator-reported for 85 calls. Persisted sums include all v4 rows on the active revision (including a second v4 row for calibration opportunity C if force-reassessed after the batch).

## 3. Relevance distribution

```json
{
  "WEAK_FIT": 45,
  "OUT_OF_SCOPE": 24,
  "MODERATE_FIT": 12,
  "STRONG_FIT": 5
}
```

## 4. Relevance × human review

```json
{
  "WEAK_FIT": {
    "DISMISS": 37,
    "UNREVIEWED": 8
  },
  "OUT_OF_SCOPE": {
    "DISMISS": 16,
    "UNREVIEWED": 8
  },
  "MODERATE_FIT": {
    "UNREVIEWED": 7,
    "DISMISS": 5
  },
  "STRONG_FIT": {
    "UNREVIEWED": 5
  }
}
```

## 5. DISMISS disagreement analysis

Total DISMISS in audit set: **58**

```json
{
  "WEAK_FIT": 37,
  "OUT_OF_SCOPE": 16,
  "MODERATE_FIT": 5
}
```

## 6. WEAK_FIT analysis

```json
{
  "other": {
    "count": 34,
    "example_titles": [
      "Administration Specialist",
      "Administrative Officer (SURAGGWA \u2013 Programme Coordination Unit/PCU)",
      "Agrifood Systems Specialist (SC 7)",
      "Analista de Ci\u00eancia de Dados (1 vaga) (Home Based) - [Open to internal and external applicants] - Br",
      "Analista en Desarrollo Productivo Sostenible (Abierto a candidatos internos y externos) - Mexico, Me"
    ],
    "review_distribution": {
      "DISMISS": 28,
      "UNREVIEWED": 6
    }
  },
  "monitoring_evaluation_research": {
    "count": 5,
    "example_titles": [
      "Call for Experts | Research, Data Analysis, Community Engagement & Strategic Communications - Sierra",
      "Endline Evaluation of the Strategic Partnership Agreement II Programme and Syria & Lebanon Top Ups",
      "Monitoring Evaluation Accountability Learning (MEAL) Specialist",
      "Monitoring, Evaluation and Learning Specialist",
      "Research and Data Analysis Specialist"
    ],
    "review_distribution": {
      "DISMISS": 3,
      "UNREVIEWED": 2
    }
  },
  "environment_climate_spatial": {
    "count": 3,
    "example_titles": [
      "Climate Change Specialist (Anticipatory Action)",
      "Climate Resilience and Environmental Specialist",
      "TA-10310 UZB: Preparing the Accelerating the Climate Transition for Green, Inclusive, and Resilient "
    ],
    "review_distribution": {
      "DISMISS": 3
    }
  },
  "land_governance_adjacent": {
    "count": 2,
    "example_titles": [
      "GRANT-0933 PAK: Women Inclusive Finance Sector Development Program (Subprogram 1) - Nationwide Basel",
      "LOAN E-059010-001 CAM: Smallholder Resilient Economic Development Sector Project - SRED-SP/CS-003 Ba"
    ],
    "review_distribution": {
      "DISMISS": 2
    }
  },
  "project_management": {
    "count": 1,
    "example_titles": [
      "Project Manager - Technical Assistance"
    ],
    "review_distribution": {
      "DISMISS": 1
    }
  }
}
```

## 7. STRONG / MODERATE inspection

See `strong_moderate_inspection` in JSON (17 rows).

## 8. OUT_OF_SCOPE false-negative candidates

Keyword-flagged candidates for manual review: **0** (see JSON; not automatic ground truth).

## 9. Relevance × ranking

```json
{
  "WEAK_FIT": {
    "LOW": 44,
    "MEDIUM": 1
  },
  "OUT_OF_SCOPE": {
    "LOW": 24
  },
  "MODERATE_FIT": {
    "MEDIUM": 10,
    "HIGH": 1
  },
  "STRONG_FIT": {
    "HIGH": 5
  }
}
```

## 10. Queue policy simulation

```json
{
  "policy_A_exclude_oos_only": {
    "policy": "A",
    "primary_queue_size": 62,
    "secondary_queue_size": 0,
    "hidden_out_of_scope": 24,
    "needs_review_queue": 0,
    "dismiss_in_primary": 42,
    "shortlist_excluded_from_primary": 0,
    "geo_title_scope_oos_candidates": [],
    "geo_title_scope_oos_candidate_count": 0
  },
  "policy_B_exclude_oos_unknown_separate": {
    "policy": "B",
    "primary_queue_size": 62,
    "secondary_queue_size": 0,
    "hidden_out_of_scope": 24,
    "needs_review_queue": 0,
    "dismiss_in_primary": 42,
    "shortlist_excluded_from_primary": 0,
    "geo_title_scope_oos_candidates": [],
    "geo_title_scope_oos_candidate_count": 0
  },
  "policy_C_primary_strong_moderate": {
    "policy": "C",
    "primary_queue_size": 17,
    "secondary_queue_size": 45,
    "hidden_out_of_scope": 24,
    "needs_review_queue": 0,
    "dismiss_in_primary": 5,
    "shortlist_excluded_from_primary": 0,
    "geo_title_scope_oos_candidates": [],
    "geo_title_scope_oos_candidate_count": 0
  }
}
```

## 11. Token statistics

```json
{
  "prompt_tokens": {
    "count": 86,
    "sum": 814491,
    "mean": 9470,
    "median": 9272,
    "p90": 10350,
    "min": 8707,
    "max": 11538
  },
  "completion_tokens": {
    "count": 86,
    "sum": 240040,
    "mean": 2791,
    "median": 2789,
    "p90": 3838,
    "min": 688,
    "max": 4625
  },
  "total_tokens": {
    "count": 86,
    "sum": 1054531,
    "mean": 12261,
    "median": 12122,
    "p90": 13621,
    "min": 9791,
    "max": 15516
  }
}
```

## 12. Recommended 17G-2B design

1. **Hide OUT_OF_SCOPE from default queue?** Yes, with audit view — 24/86 (28%) OUT_OF_SCOPE; 16/58 DISMISS align; no STRONG/MODERATE among DISMISS.
2. **Audit view for OUT_OF_SCOPE?** Required; retain full assessment history.
3. **WEAK_FIT in normal queue?** Yes — 45/86 (52%); 37 DISMISS + 8 UNREVIEWED; primary triage band, not hidden with OOS.
4. **Primary/secondary queues?** Policy C (17 STRONG+MODERATE primary, 45 WEAK secondary) matches intent; optional UI filter, not separate persistence.
5. **UNKNOWN / INSUFFICIENT_EVIDENCE?** None in v4 set; future: needs-review queue, never default.
6. **LOW band auto-hide?** No — LOW mixes WEAK_FIT (44) and OUT_OF_SCOPE (24); gate on relevance, not band.
7. **Ranking changes now?** No — implement relevance gate first; re-rank after v4 already applied where batch ran.
8. **False-negative protection?** Manual review list for OOS with geo/cadastre titles; do not auto-promote.
9. **Human review vs visibility?** Independent audit dimension; DISMISS does not auto-hide WEAK_FIT; optional “dismissed” filter only.
10. **17G-2B scope:** Default `OpportunityReviewQueryService` excludes OUT_OF_SCOPE; `include_irrelevant=true` (or equivalent) shows them; WEAK_FIT+ remain; dashboard counts document semantics; no review/ranking/schema changes.

## 13. Risks / safeguards

- Do not hide WEAK_FIT solely because of DISMISS history.
- OUT_OF_SCOPE + geo keyword hits require manual false-negative review before tightening gate.
- UNKNOWN / INSUFFICIENT_EVIDENCE → needs-review queue, not default.

## 14. Reproduce

```bash
python scripts/analyze_v4_decision_quality.py
```
