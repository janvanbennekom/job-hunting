# Phase 17H-0 — Operator UI performance audit

**Investigation only.** No production code, schema, or data changes. No OpenAI calls.

**Measured environment:** local operator DB with **105** canonical opportunities (production-scale), read-only benchmark run `2026-09-30`.

---

## 1. Executive summary

The Streamlit UI feels slow primarily because **backend read paths perform O(N) SQL round-trips per opportunity**, not because ~100 rows exceed Streamlit’s table limits.

At **105 opportunities**, a single `OpportunityReviewQueryService.list_queue()` issued **~1,469 SQL statements** in **~26s**. The Opportunities page runs **two** full queue builds per rerun (`count_relevance_segments` + `list_queue`), totalling **~2,397 SQL / ~44s** before `st.data_editor` renders **6 Primary rows**.

**Opportunity Detail** accidentally repeats the entire queue: `_build_ranking` calls `list_queue()` over the full population to resolve one `dynamic_rank` (**~1,493 SQL / ~27s** for one detail view).

Home is similarly heavy: bulk assessed/ranked counts are optimised, but **HIGH preview** and **relevance segment counts** still call `list_queue()`-class paths (**~2,410 SQL / ~44s**).

Streamlit **engine lifecycle is correct** (`@st.cache_resource` on session factory). The gap vs `/status` is **missing bulk pipeline assembly** on queue/detail paths, plus **duplicate traversals** introduced or amplified by 17G-2B segment counts and detail ranking.

**Priority for 17H-1:** bulk-load assessments/rankings/eligibility/sources for active revision; single-pass queue build; remove detail-page full `list_queue`; fold segment counts into one pass; defer `st.cache_data` until semantics are clear.

---

## 2. Current page architecture

### 2.1 Shared bootstrap

| Layer | Behaviour |
|--------|-----------|
| `ui/streamlit/bootstrap.py` | `@st.cache_resource get_session_factory()` → one **Engine** + **sessionmaker** per Streamlit worker process |
| Each rerun | New `Session` per `with session_factory() as session` block |
| Sidebar | Cheap; optional fake-assessment toggle only |

### 2.2 Home (`pages/home.py`)

```
render_sidebar()
→ DashboardSummaryService.build_summary(allow_fake)
   → list_all opportunities (1 query)
   → list_for_revision assessments + rankings (2 queries)
   → compute_production_dashboard_counts() [in-memory, bulk — Phase /status pattern]
   → count_relevance_segments() → full list_queue() [N+1 pipeline]
   → high_priority_preview → list_queue(HIGH band) [N+1 pipeline, still scans all opps in loop]
→ Streamlit metrics + dataframes + buttons
```

### 2.3 Opportunities (`pages/opportunities.py`)

```
render_sidebar()
→ build OpportunityQueueFilters (query params: eligibility, lifecycle, ranking_band, relevance_queue)
→ Session 1: count_relevance_segments(base_filters)  → list_queue (no segment, no hide)
→ st.radio relevance queue (rerun on change via query param)
→ hide dismissed checkbox
→ Session 2: list_queue(filters with segment + hide_dismissed)
→ optional Python filter for human review dropdown
→ build_opportunity_queue_dataframe(items)
→ st.data_editor + bulk review UI
```

### 2.4 Opportunity Detail (`pages/opportunity_detail.py`)

```
render_sidebar()
→ OpportunityDetailService.get_detail(one id)
   → pipeline.load (per-opp N+1)
   → sources, observations, eligibility rules, review history, pursuit, assessment presentation
   → _build_ranking → list_queue() over **entire** queue to find dynamic_rank  ← critical
→ render_* sections (no second full queue in UI)
```

---

## 3. Home — query count and timing

| Metric | Measured (N=105) |
|--------|------------------|
| SQL statements | **2,410** (~23/opp) |
| Wall time (backend only) | **~44.0s** |

**Breakdown (by code inspection + counts):**

- **O(1) bulk:** `list_for_revision` assessments/rankings; `compute_production_dashboard_counts`.
- **O(N):** `count_relevance_segments` ≈ one full `list_queue`.
- **O(N):** HIGH preview `list_queue` with `ranking_band=HIGH` — still iterates **all** opportunities and runs `_build_item` before band filter.

Human-review and relevance dimensions are not on Home; cost is almost entirely **duplicate queue traversal**.

---

## 4. Opportunities — query count and timing

### 4.1 Measured (N=105, Primary segment, 6 rows shown)

| Step | SQL | Time |
|------|-----|------|
| `list_queue` once | 1,469 | 26.5s |
| Full page backend (counts + list + dataframe) | 2,397 | 43.7s |
| Ratio vs single `list_queue` | ~1.63× | ~1.65× |

17G-2B **`count_relevance_segments`** calls `list_queue` with `relevance_queue=None`, building pipeline state for **every** opportunity, then counts in memory. The displayed queue runs **`list_queue` again** with segment/hide filters — filters apply after `_build_item`, so **cost is still Θ(N)** on full corpus.

### 4.2 Per-opportunity work inside `list_queue`

For each opportunity in `list_all()`:

| Step | Queries (typical) | Bulk today? |
|------|-------------------|-------------|
| `OpportunityPipelineReader.load()` | **~5–8+** | No |
| `list_for_opportunity` sources | 1 | No |
| `get_latest_for_opportunity_and_revision` eligibility | 1 | No |
| `JobSourceRepository.get_by_id` (primary link) | 1 | No |
| Human review | **0** (bulk `map_latest_by_opportunity_ids`) | **Yes** |

**`PipelineReader.load` per call:**

1. `get_latest_success_for_revision` (production) — SELECT  
2. `list_for_opportunity` (all assessments) — SELECT  
3. `get_latest_success_for_revision` (display) — SELECT again  
4. `list_for_opportunity_and_revision` rankings — SELECT  
5. `get_by_id` per distinct `profile_assessment_id` on rankings — 0–k SELECTs  

**`_order_queue` (second pass):** for each **ranked** row in the filtered set, `get_by_id` + **`pipeline.load` again** → up to **~2× pipeline** per ranked opportunity.

### 4.3 Scaling estimate (`list_queue` / Opportunities backend)

Assuming measured **~14 SQL/opportunity** and **~0.25s/opportunity** (remote DB latency included):

| N (opportunities) | SQL (1× list_queue) | SQL (Opportunities page ≈1.6×) | Est. backend time (page) |
|-------------------|----------------------|--------------------------------|---------------------------|
| 10 | ~140 | ~230 | ~4s |
| 100 | ~1,400 | ~2,300 | ~40s |
| 105 (measured) | 1,469 | 2,397 | 44s |
| 500 | ~7,000 | ~11,500 | ~3.5 min |
| 1,000 | ~14,000 | ~23,000 | ~7 min |

Complexity: **O(N)** SQL and CPU for queue build; **not** O(1) or O(log N).

Filters (lifecycle, eligibility, relevance segment) **do not reduce** work before `_build_item` except `source_id` pre-filter.

---

## 5. Detail — query count and timing

| Metric | Measured (N=105, one opportunity) |
|--------|-----------------------------------|
| SQL | **1,493** |
| Time | **~27.1s** |

**~99% of detail slowness is `list_queue()` inside `_build_ranking`**, not single-opp facts/assessment/eligibility.

Without that call, detail would be **O(1)** queries for one opportunity (plus observations/rules history).

---

## 6. N+1 findings (ranked by impact)

| # | Finding | Severity | Location |
|---|---------|----------|----------|
| 1 | Full `list_queue()` on detail for `dynamic_rank` | **Critical** | `opportunity_detail.py` `_build_ranking` |
| 2 | Per-opp `OpportunityPipelineReader.load()` | **Critical** | `opportunity_query._build_item`, `_order_queue` |
| 3 | Double `list_queue` on Opportunities (segment counts + display) | **High** | `opportunities.py`, `count_relevance_segments` |
| 4 | Home relevance counts + HIGH preview = 2× queue traversal | **High** | `dashboard_summary.py` |
| 5 | Per-opp eligibility `get_latest_*` | Medium | `_build_item` |
| 6 | Per-opp source links + `JobSource.get_by_id` | Medium | `_build_item`, `source_links` |
| 7 | Duplicate `get_latest_success_for_revision` in pipeline | Medium | `opportunity_reads.py` |
| 8 | `list_for_opportunity` assessments loaded entirely for “latest any” | Medium | `_latest_assessment_any` |
| 9 | Human review | **Fixed (bulk)** | `map_latest_by_opportunity_ids` |

**Reusable bulk patterns (already exist):**

- `list_for_revision` assessments/rankings + `compute_production_dashboard_counts` (`dashboard_metrics.py`)
- `map_latest_by_opportunity_ids` reviews

**Not yet used for Opportunities queue.**

---

## 7. Streamlit rerun behaviour

Streamlit reruns the **entire script** on widget interaction.

| Action | Rerun? | Re-executes expensive backend? |
|--------|--------|--------------------------------|
| Relevance queue radio | Yes (`st.rerun` + query param) | **Yes** — both segment count + list_queue |
| Lifecycle / ranking / review selectboxes | Yes | **Yes** |
| Hide dismissed | Yes | **Yes** |
| Include ineligible / non-actionable | Yes | **Yes** |
| Location / source text inputs | Yes (on change) | **Yes** |
| Checkbox in `st.data_editor` | Yes | **Yes** — full backend **before** editor |
| Bulk action buttons | Yes | **Yes**; commit only on confirm |
| Return from Detail (navigation) | Yes | **Yes** |
| Sidebar fake-assessment toggle | Yes | **Yes** |

**Checkbox selection is especially costly:** every tick rebuilds the queue even though selection state is client-side in `session_state`.

### Cache candidates (do **not** implement in 17H-0)

| Candidate | Risk | Notes |
|-----------|------|-------|
| `st.cache_data(list_queue, filters…)` | **High** | Assessments/reviews change; TTL invalidation hard |
| `st.cache_data(segment_counts)` | Medium | Same |
| `st.cache_resource(session_factory)` | **Already used** | Correct |
| `st.cache_data(build_summary)` | Medium | Scan/assessment updates |
| Fragment/`st.form` for filters | Low–medium | Could limit reruns (17H-1 UI pattern) |

Prefer **faster idempotent reads** over caching mutable queue data.

---

## 8. Engine / session lifecycle

| Component | Streamlit operator UI | Public `/status` |
|-----------|----------------------|------------------|
| Engine | Cached via `get_session_factory` | Module singleton in `server.py` |
| Pool | One per worker | One per process |
| Session | New per `with session_factory()` | New per `/status` request |

**Appropriate for Streamlit** — no need to recreate engine each rerun.

Opportunities uses **two sessions per rerun** (segment counts vs list); minor overhead vs query storm.

---

## 9. `st.data_editor` findings

Measured Primary view: **6 rows** after filters; dataframe build is **negligible** (<1ms class).

Backend preparation **~44s** dominates; **no evidence** that `st.data_editor` is the bottleneck at current scale.

At **Weak fit (~45 rows)** or **500 opportunities** without pre-filtering pipeline work, backend would still dominate; editor cost may become noticeable (~100–500ms range) but secondary until N+1 is fixed.

**Recommendation:** optimise DB/service layer first; profile Streamlit widget time in 17H-1 only if backend <2s and UI still slow.

---

## 10. Scaling summary

| N | list_queue SQL (est.) | Opportunities page SQL (est.) | Detail (today) |
|---|------------------------|-------------------------------|----------------|
| 100 | ~1,400 | ~2,300 | ~1,400 (full queue) |
| 500 | ~7,000 | ~11,500 | ~7,000 |
| 1,000 | ~14,000 | ~23,000 | ~14,000 |

Detail row should be **O(1)** after fix; today it stays **O(N)**.

---

## 11. Ranked bottlenecks (measured impact @ N=105)

1. **Per-opportunity pipeline SQL** (~26s / 1,469 queries per `list_queue`)  
2. **Duplicate full queue on Opportunities page** (+~17s / +~900 queries)  
3. **Detail `list_queue` for rank** (~27s / ~1,493 queries)  
4. **Home double queue** (counts + HIGH preview) (~44s total)  
5. **`_order_queue` second `pipeline.load`** (multiplier on ranked subset)  
6. Streamlit full-script rerun (amplifies 1–5 on every interaction)  
7. `st.data_editor` (not material at current row counts)

---

## 12. Recommended optimisations (for 17H-1 planning)

| Priority | Change | Expected benefit | Complexity | Regression risk |
|----------|--------|------------------|------------|-----------------|
| P0 | Bulk pipeline read model for active revision (reuse `list_for_revision` + in-memory selection like `dashboard_metrics`) | **~10–20×** fewer SQL; **~10–20×** faster queue | Medium | Medium — must match production_selection semantics |
| P0 | Remove `list_queue` from detail; compute rank from bulk map or skip global rank on detail | Detail **~27s → <1s** | Low | Low |
| P1 | Single-pass segment counts + queue build (one traversal, count buckets while building) | Opportunities **~1.6× → ~1×** list cost | Low | Low |
| P1 | Bulk eligibility latest-by-revision; bulk opportunity sources + job sources | −2N queries | Medium | Low |
| P2 | Eliminate duplicate `pipeline.load` in `_order_queue` (reuse first pass ranking) | −up to N pipeline loads | Low | Low |
| P2 | Home: optional relevance/HIGH preview off main path or share bulk read model | Home **~44s → few seconds** | Medium | Low |
| P3 | `st.form` / fragments for filter bar to avoid rerun on unrelated widgets | Fewer reruns | Medium | UX change |
| P4 | `st.cache_data` on immutable revision-scoped snapshot | Variable | Medium | **High** if stale |
| P5 | Replace Streamlit | Only if backend <2s and UI still slow | Very high | N/A now |

---

## 13. Proposed Phase 17H-1 plan

1. **`OpportunityPipelineBulkReader`** (or extend `OpportunityPipelineReader` with `load_all_for_revision`) using existing `list_for_revision` assessments/rankings and the same `select_production_ranking` / `assessment_display_state` helpers as `dashboard_metrics.py`.  
2. **Refactor `OpportunityReviewQueryService.list_queue`** to one bulk load + in-memory assembly; preserve filter/sort semantics (17G-2B relevance, hide dismissed).  
3. **`count_relevance_segments`** → tallies from the same built items (or shared cache within request scope).  
4. **Detail `_build_ranking`:** accept `dynamic_rank` from a narrow query or precomputed rank map for one id — **never** full queue.  
5. **Home `build_summary`:** reuse bulk reader for preview + relevance counts.  
6. **Tests:** query-count ceilings for N=10/50; timing regression guard (CI threshold).  
7. **Optional UI:** wrap filters in `st.form` (“Apply filters”) to stop rerun on every keystroke.  
8. **Defer** `st.cache_data` until bulk path is stable and invalidation strategy is documented.

---

## Appendix A — Instrumentation

| Artifact | Purpose |
|----------|---------|
| `scripts/benchmark_ui_read_paths.py` | SQL count + wall time for Home, Opportunities, Detail |
| `tests/application/test_ui_read_path_query_scaling.py` | Assert SQL grows with +1 opportunity |

**Benchmark command (read-only on existing data):**

```bash
python scripts/benchmark_ui_read_paths.py
```

**Synthetic scaling (rolls back; blocked when `JOBHUNTER_ENV=production`):**

```bash
python scripts/benchmark_ui_read_paths.py --synthetic-seed 100
```

---

## Appendix B — Safety confirmation

- **Production writes:** none during investigation benchmark (read-only SELECTs).  
- **OpenAI calls:** none.  
- **Alembic head (at audit time):** `20260929_0015`.  
- **Production code / schema:** unchanged.
