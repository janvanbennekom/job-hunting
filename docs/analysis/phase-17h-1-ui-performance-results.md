# Phase 17H-1 — UI read-path performance results

Baseline: [phase-17h-0-ui-performance-audit.md](./phase-17h-0-ui-performance-audit.md).

**Environment:** Windows dev host, PostgreSQL (same read-only dataset as 17H-0), **105** canonical opportunities, **86** eligible+actionable in default queue, **6** Primary rows with default filters. Measurements are **backend-only** (`scripts/benchmark_ui_read_paths.py`), excluding Streamlit rendering.

## BEFORE vs AFTER

| Path | BEFORE SQL | AFTER SQL | BEFORE time | AFTER time |
|------|------------|-----------|-------------|------------|
| Home `build_summary` | 2,410 | **22** | ~44s | **0.61s** |
| Opportunities page (counts + Primary queue + dataframe) | 2,397 | **24** | ~44s | **0.29s** |
| `list_queue` once | 1,469 | **12** | ~26s | **0.26s** |
| Opportunity Detail `get_detail` | 1,493 | **36** | ~27s | **0.80s** |

SQL is **approximately O(1)** vs opportunity count (per-opp ratio dropped from ~14–23 to &lt;0.3 including fixed overhead).

Detail retains per-opportunity queries for facts, observations, eligibility rules, and a single `pipeline.load` for assessment presentation; it no longer runs a full N+1 `list_queue()`.

## Architecture delivered

- `pipeline_assembly.py` — shared production/display assessment + ranking selection.
- `pipeline_bulk.py` — `OpportunityPipelineBulkIndex.load()` (2 revision-wide SELECTs + in-memory index).
- `queue_snapshot.py` — `OpportunityQueueSnapshot` for segment counts and filtered lists in one bulk load.
- Repository bulk helpers: `map_latest_for_revision`, `map_all_grouped_by_opportunity`, `map_all_by_id` (job sources).
- `OpportunityReviewQueryService.list_queue_with_snapshot()` for single-load use cases (benchmark/Home); Opportunities UI uses counts + list (two bulk loads per rerun, still O(1) SQL each).

## Streamlit (secondary)

No `st.form` change in 17H-1; backend fix dominates. Checkbox/radio reruns still re-run bulk loads (~24 SQL), which is acceptable at measured timings.

## Regression tests

- `test_pipeline_bulk_parity.py` — bulk vs `OpportunityPipelineReader`.
- `test_ui_read_path_query_scaling.py` — SQL bounded when adding synthetic opportunities.
