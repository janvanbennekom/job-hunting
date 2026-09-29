# Phase 17G-1A — Assessment payload optimisation

## Payload architecture (before → after)

| Aspect | Pre-17G-1A (v2 baseline) | Post-17G-1A (v3) |
|--------|---------------------------|------------------|
| Schema | `profile_assessment_v2` | `profile_assessment_v3` |
| Opportunity | `opportunity_prompt_text` **and** duplicate `opportunity` object | `opportunity_prompt_text` only (+ sufficiency, strategy fields) |
| Evidence pack | Full catalog assignments (10), all 9 services, `selection_notes` | Top 5 assignments, top 4 services, truncated verbose fields, **no** `selection_notes` |
| Digest reuse | `input_digest` tied to full profile evidence ids | Adds `model_evidence_digest` (actual model payload) |
| Usage | Discarded | `prompt_tokens`, `completion_tokens`, `total_tokens` on assessment row |

## Evidence selection

- Tokenise opportunity title, description, location, organisation; expand domain synonym groups (land/cadastre, LIS, GIS, SDI, integration).
- **Services:** score = token overlap on name + description; sort `(score, name)` desc; take 4.
- **Assignments:** score = overlap on concatenated project_name, role, description, responsibilities, tools, country, donor; sort `(score, last_active_year, project_name)` desc; take 5.
- Capabilities/skills/countries: existing caps (12 / 15 / 8 fallback) unchanged.

## Model-only serialization

`evidence_pack_to_model_mapping()` omits `selection_notes`; truncates assignment description/responsibilities (700 chars) and service description (400).

## Digest semantics

- `profile_evidence_digest`: full catalog entity id sets (unchanged column semantics).
- `model_evidence_digest`: SHA-256 of `evidence_pack_to_model_mapping(pack)` — selection, truncation, excluded notes.
- `input_digest`: hashes opportunity content, both digests, search strategy revision, **v3** schema version, model id.
- Changing `selection_notes` alone does **not** change `model_evidence_digest` or `input_digest`.

## Production population (n=92, offline estimate)

See `phase-17g-1a-token-cost-estimate.json`.

| Metric | Legacy v2 median | v3 median | Reduction |
|--------|------------------|-----------|-----------|
| Total chars | 50,290 | 30,536 | ~39% |
| Est. input tokens | 12,572 | 7,633 | ~39% |

Median est. tokens (~7.6k) is above the 4k–6k aspiration: `profile_other` (positioning + capabilities + skills + languages + countries) remains ~11.7k chars median and was not aggressively trimmed in this phase to avoid relevance regression.

## Pilot (do not run until deployed)

After migration `20260929_0015`, reassess three diverse opportunities (e.g. land/LIS, GIS/SDI, digital transformation) with `force=True`, verify `overall_relevance`, token columns, and digest reuse.
