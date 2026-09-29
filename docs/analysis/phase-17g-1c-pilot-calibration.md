# Phase 17G-1C — Pilot calibration and reassessment preparation

## Pilot warnings (A–E)

All five v3 assessments are **SUCCEEDED_WITH_WARNINGS** because `AssessmentValidationService.validate()` produced a non-empty `warnings` list; `OpportunityProfileAssessmentService` sets status to `SUCCEEDED_WITH_WARNINGS` when `validation.warnings` is truthy (otherwise `SUCCEEDED`).

Shared warning patterns:

| Warning | Cause | Severity |
|---------|--------|----------|
| `rejected opportunity excerpt not found in DESCRIPTION` | Model `opportunity_refs` excerpts were not exact substrings of supplied opportunity text | Benign compliance / grounding loss for those refs |
| `skipped non-object assignment_evidence` (and capability/skill/language/country) | Model returned non-object elements (often strings) in evidence arrays | Quality issue: grounded evidence dropped; overall relevance still persisted |

These are **not** failures. They indicate the model partially ignored output shape and excerpt rules. v4 prompt/schema wording now stresses object-shaped evidence arrays and exact excerpts; schema bumped to **profile_assessment_v4** so reassessment picks up new semantics.

## STRONG vs MODERATE (pilot C)

Pilot C (generic IT and Digitalisation Officer, PARTIAL sufficiency) received **STRONG_FIT** while rationale noted limited land-specific detail. Under v3 instructions, STRONG_FIT was broad enough to allow strong profile IT evidence to dominate.

**v4 instruction change:** STRONG_FIT requires the opportunity’s substantive work to centre land/geospatial/digital-transformation-for-land-agencies scope; broad generic digitalisation without that focus should be **MODERATE_FIT** at most.

## Ranking vs OUT_OF_SCOPE (D/E)

Pilot v3 assessments are **OUT_OF_SCOPE**, but current **RANKED / score 50 / LOW** rankings remain linked to **profile_assessment_v1** with **UNKNOWN** (50 relevance points). Rankings were **not** re-run after the pilot. `rank_opportunity` after reassessment would use v4/v3 OUT_OF_SCOPE (100 points) but still produce RANKED + LOW band — ranking_v1 does not exclude OUT_OF_SCOPE from ranking.

## Reassessment population (read-only, v4 head)

Run: `python scripts/summarize_reassessment_population.py`

Rule: **ELIGIBLE** + actionable lifecycle (`NEW`, `UPDATED`, `STILL_OPEN`); paid call only if no reusable successful assessment for current `input_digest` (includes **v4** schema).

At v4 head: **86** paid calls among **86** actionable+eligible (pilot v3 rows do not reuse).

## Token forecast (from five pilot calls)

| | Prompt | Completion | Total |
|--|--------|------------|-------|
| Mean | 9341 | 1672 | 11014 |
| Median | 9022 | 1678 | — |
| Range (observed) | 8544–10187 | 1536–1843 | 10104–11723 |

Base estimate for 86 calls (median prompt, mean completion/total): ~776k prompt, ~144k completion, ~947k total tokens.

## Pilot token observation

Actual median prompt **9022** vs offline estimate **7633** (~18% higher). OUT_OF_SCOPE D/E prompts largest (~10k)—likely longer opportunity text and fuller negative-evidence narrative; defer further payload cuts until discrimination stabilises on v4.

## Reassessment tooling

`scripts/run_profile_reassessment.py` — **dry-run by default**; `--apply` for live calls; `--limit`, `--delay-seconds`; reuses digest; ranks after success; token summary at end.

## 17G-2 acceptance criteria (draft)

See final report section in commit message / AGENTS follow-up.
