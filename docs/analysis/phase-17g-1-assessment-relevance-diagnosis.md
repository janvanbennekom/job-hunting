# Phase 17G-1 — Assessment relevance diagnosis and fix

## Root cause

Production assessments were **not losing fields in parsing or persistence**. The OpenAI adapter returned JSON that **validated successfully** while using:

1. **No output contract in the API call** — only `response_format: json_object`, with input data in the user message and **no required output schema or enum semantics**.
2. **Prompting that favoured UNKNOWN** — system and per-request instructions told the model to use UNKNOWN/INSUFFICIENT_EVIDENCE “when appropriate” and to assess “conservatively”.
3. **Validation defaults** — missing `overall_relevance` defaults to `UNKNOWN`; empty `professional_relevance` and `rationale` are accepted.
4. **Model behaviour** — `gpt-5.4-mini` returned `SUCCEEDED` assessments with `overall_relevance: UNKNOWN` and empty narrative fields even when profile evidence (~60k chars request) and **ADEQUATE** opportunity text were present.

Raw OpenAI responses are **not persisted** (only validated `result` JSON).

## Code locations

| Area | File |
|------|------|
| OpenAI request | `src/jobhunter/ai/openai_model.py` |
| Per-request instructions | `src/jobhunter/application/profile_assessment/service.py` (`_instructions_for_sufficiency`) |
| Default UNKNOWN | `src/jobhunter/application/profile_assessment/validation.py` (`raw.get("overall_relevance", "UNKNOWN")`) |
| Output contract (new) | `src/jobhunter/application/profile_assessment/output_schema.py` |
| Empty UNKNOWN rejection (new) | `validation.py` `_reject_empty_unknown_relevance` |
| Schema version bump | `src/jobhunter/domain/assessment_enums.py` → `profile_assessment_v2` |
| Persistence | `validation.result.to_mapping()` unchanged |

## UNKNOWN semantics (after fix)

- **UNKNOWN**: genuinely insufficient source text to judge professional relevance.
- **OUT_OF_SCOPE**: clear discipline mismatch when posting is sufficient (e.g. Civil Engineer, HSSE, GESI).
- **Not allowed**: UNKNOWN with ADEQUATE/PARTIAL sufficiency, ≥200 chars of opportunity text, and empty `scope_summary` + `rationale` → **FAILED_VALIDATION** (triggers retry on next assess).

## Production trace (examples)

| Sample | Sufficiency | Profile in request | Persisted |
|--------|-------------|------------------|-----------|
| HSSE Officer | ADEQUATE | 9 services, 10 assignments | UNKNOWN, empty rationale |
| Civil Engineer | ADEQUATE | full pack, 6269 char description | UNKNOWN, empty rationale |
| Gender Specialist | ADEQUATE | full pack | UNKNOWN, empty rationale |

## Reassessment

- **~91** OpenAI `SUCCEEDED` rows (all UNKNOWN, empty narrative) need **re-assessment** with `force=True` or after input digest change.
- Bumping `PROFILE_ASSESSMENT_SCHEMA_VERSION` to **v2** changes `input_digest` → new assessments will not reuse v1 rows automatically.

## Live OpenAI calls (investigation)

**0** live calls during this phase.
