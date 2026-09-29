# Phase 17G-1 — OpenAI assessment token & cost architecture (investigation)

**No live OpenAI calls.** Estimates from production DB + dry-run request construction (`scripts/estimate_assessment_token_cost.py`).

---

## Production model

| Source | Value |
|--------|--------|
| `JOBHUNTER_OPENAI_MODEL` (`.env`) | **gpt-5.4-mini** |
| Persisted `opportunity_profile_assessments.model_name` | **gpt-5.4-mini** (91 rows) |
| OpenAI adapter | `OpenAIAssessmentModel` — `model=self.model_name`, **no `max_tokens`** |

**Max output tokens:** not set in code; provider/model default applies (completion bounded by model, not application config).

---

## Token usage persistence & logging

| Item | Status |
|------|--------|
| `completion.usage` in API response | Captured in `AssessmentModelResponse.usage` |
| Persisted on `OpportunityProfileAssessment` | **No** |
| Application logs | **No** token logging found |
| Reconciliation with OpenAI dashboard | Must use provider dashboard; **40** OpenAI assessments on **2026-09-29** in DB (other API use e.g. strategy chat may share the same key/model) |

---

## Prompt size (current `profile_assessment_v2` payload)

Median over **92** opportunities (dry-run):

| Component | Median chars | ~Median tokens (÷4) | Notes |
|-----------|-------------:|--------------------:|-------|
| **evidence_pack** | 40,306 | ~10,077 | Dominates input |
| → professional_services | 3,968 | | **All 9 active services every time** |
| → assignments (top 10) | 16,809 | | Full project text; count always **10** |
| → capabilities (top 12) | 5,730 | | |
| → skills (top 15) | 3,272 | | |
| → languages (all) | 1,050 | | **All languages every time** |
| → countries | 1,087 | | Up to 8 |
| → selection_notes | 8,345 | | **Per-request metadata; not needed for model reasoning** |
| → positioning_summary | 630 | | |
| **opportunity_prompt_text** | 823 | ~206 | Title + fields; DESCRIPTION median **291** chars |
| **opportunity** object (duplicate) | 786 | ~197 | Repeats title/description/dates |
| **strategy_and_meta** | 4,855 | ~1,214 | 9 themes + preferences + eligibility summaries + instructions |
| **output_schema + instructions** | 2,580 | ~645 | Added in 17G-1 user payload wrapper |
| **full user JSON (v2)** | 49,587 | ~12,397 | |
| **system + user message** | 50,290 | **~12,572** | |

**P90** system+user: **~63,126 chars (~15.8k tokens)** — driven by long descriptions (max **12,000** per field cap in `opportunity_prompt.py`).

Pre-17G-1, `assessment_input` alone was ~**59,495** chars for Civil Engineer sample (no output schema wrapper).

---

## Per-assessment token estimate (for pricing)

Use OpenAI’s current **gpt-5.4-mini** price list externally.

| | Tokens (estimate) |
|--|------------------:|
| Input (median) | **~12,600** |
| Output (assumed JSON assessment) | **~400** (minimal/empty) to **~800–1,500** (rich structured) |
| **Total per call (median planning)** | **~13,000** |

**Reassessment totals (input+400 output, median per opp):**

| Opportunities | ~Total tokens |
|---------------|-------------:|
| 10 | 130k |
| 65 | 843k |
| 86 | 1.12M |
| 91 | 1.18M |

Multiply by published $/1M input and $/1M output for USD.

**Sept 29 sanity check:** 40 assessments × ~12.6k input ≈ **504k input tokens** (+ ~16k output). Dashboard **$4.41** same day may include non-assessment calls (strategy interpreter uses the same `JOBHUNTER_OPENAI_MODEL` with smaller prompts).

---

## Is the evidence pack the same for every opportunity?

**Mostly yes, with minor variation:**

| Element | Per-opportunity variation |
|---------|---------------------------|
| Professional services | **No** — always **9/9** active |
| Assignments | **Order/content of top 10** — token overlap ~36.5k–42.2k pack size |
| Capabilities / skills | Top-N by token overlap with title |
| Languages | **No** — all included |
| selection_notes | Text changes (scores/reasons) — **~8.3k chars** |

So ~**80%+** of input tokens are **profile/strategy context** repeated on every call, not opportunity-specific text.

---

## Cost-reduction design (recommended — not implemented)

Priority order (quality-preserving):

### 1. Shrink evidence_pack (largest win, low risk)

- **Drop `selection_notes` from model payload** (audit in app/logs only) → ~**8k chars (~2k tokens)** saved immediately.
- **Cap assignment fields** sent to model (e.g. 500–800 chars description/responsibilities per assignment; keep full text in DB for UI).
- **Send top 4–5 assignments** by relevance score, not 10; keep validation IDs stable.
- **Professional services:** send id + name + 1-line description, not full PS document text; or top 3–4 by relevance instead of all 9.

### 2. Compact stable profile summary (~2–4k tokens once)

- One cached **`profile_assessment_context_v1`** blob per profile revision: positioning, service list, 5 bullet assignments, key capabilities/skills — **reused for every opportunity** (digest includes profile revision).
- Full evidence only when summary assessment is MODERATE+ or WEAK_FIT (optional second pass).

### 3. Opportunity text

- **Remove duplicate `opportunity` object** from request; keep `opportunity_prompt_text` only.
- **Smart excerpt:** title + organisation + expertise/sectors + first **2–3k** chars of description + structured facts; retain 12k cap for detail-fetch sources only.
- LIST_SUMMARY_ONLY: already short; keep as-is.

### 4. Two-stage relevance (only if measured savings)

- **Stage A (cheap):** compact profile summary + opportunity excerpt → `overall_relevance` + `scope_summary` only (small JSON).
- **Stage B (current prompt):** only if not OUT_OF_SCOPE / INSUFFICIENT_EVIDENCE.
- At ~12k tokens/call today, skipping Stage B for ~50–70% OUT_OF_SCOPE could cut **total** cost ~40–50% but adds orchestration; **deterministic + Stage A** may be enough for 17G-2 gate.

### 5. Deterministic pre-filter (narrow)

- Extend **eligibility** only for **high-precision** patterns (e.g. explicit “nationality required” already there); **avoid** title-only GIS/land keyword drops (false-negative risk from 17G-0).
- Optional: skip OpenAI when eligibility is INELIGIBLE (already gated) — no change needed.

### 6. Observability (before bulk reassess)

- Persist `prompt_tokens`, `completion_tokens`, `total_tokens` on assessment row or `automation_runs` summary.
- Log per-batch totals in worker.

---

## Estimated savings (rough)

| Measure | ~Input token reduction |
|---------|------------------------:|
| Remove selection_notes + duplicate opportunity | ~2,200 |
| Services: 4 relevant + shorter fields | ~1,500 |
| Assignments: 5 × truncated | ~6,000–8,000 |
| Compact summary replacing full pack | ~8,000–10,000 |
| **Combined target** | **~12k → ~4–5k** median input |

---

## Files

- `scripts/estimate_assessment_token_cost.py` — reproducible breakdown
- `docs/analysis/phase-17g-1-token-cost-estimate.json` — machine-readable snapshot

**No production code, prompt, or model changes in this investigation.**
