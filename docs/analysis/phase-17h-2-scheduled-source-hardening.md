# Phase 17H-2 — Scheduled source execution hardening

**Date:** 2026-10-05  
**Scope:** Diagnose production worker hang; harden timeouts, logging, transactions, worker healthcheck.  
**No live production pipeline runs from this phase.**

## Root causes

1. **Single database transaction for the entire apply run** (`session_scope` in `run_scheduled_pipeline.py` wraps lock + orchestrator). `AutomationRun` was flushed but **not committed** until the pipeline finished, so operators saw **no `automation_runs` row** during a long or stuck run.

2. **Source acquisition and Phase 5 processing run inside that open transaction.** While waiting on external HTTP (or slow DevelopmentAid detail pacing), PostgreSQL showed **`idle in transaction`** with the last statement often on **`eligibility_rule_results`** (eligibility runs per opportunity after fetch).

3. **Observed hang is client-side I/O, not the advisory lock** (lock granted; `ClientRead` wait). Connectors already used a single `timeout=` float; production now uses **explicit connect + read** via `urlopen_with_timeouts` / `opener_open_with_timeouts` (tuple on Python 3.12 in Docker; read fallback where tuple is unsupported).

4. **Worker “unhealthy” in Docker** comes from the **image-level `HEALTHCHECK` on port 8501** (Streamlit). One-shot worker containers do not run Streamlit; compose now sets **`healthcheck: disable: true`** on the `worker` service.

## Source execution order

Order follows **`config/automation.json` → `sources[]`**, enabled entries only (see `AutomationConfig.enabled_sources()`).

Example production order: **FAO → DevelopmentAid → World Bank → UNDP → AfDB → TED → ADB** (ReliefWeb disabled).

## HTTP timeouts (before → after)

| Connector | Before | After (default) |
|-----------|--------|-----------------|
| FAO | 60s single | connect **15s**, read **60s** |
| DevelopmentAid | 60s single | connect **15s**, read **60s** (+ rate-limit retries/backoff unchanged) |
| World Bank | 60s | connect **15s**, read **60s** |
| UNDP | 60s | connect **15s**, read **60s** |
| AfDB | 60s | connect **15s**, read **60s** |
| TED | 90s | connect **15s**, read **90s** |
| ADB | 90s | connect **15s**, read **90s** |
| ReliefWeb | 60s | connect **15s**, read **60s** |

Override via env: `JOBHUNTER_HTTP_CONNECT_TIMEOUT`, `JOBHUNTER_HTTP_READ_TIMEOUT`.

## Logging

Stdout progress via `pipeline_progress.py` and orchestrator hooks: pipeline start/complete, per-source start/complete/fail/timeout, assessment batch, ranking, notifications, run summary.

## Transaction boundary change (minimal)

- Commit immediately after creating **`AutomationRun` (`RUNNING`)**.
- **`session.commit()`** after each source and after major downstream phases so work is not held in one long transaction across HTTP.

Larger redesign (separate session per source) is **not** done in this phase.

## Diagnostics

```bash
python scripts/diagnose_automation_sources.py --config config/automation.json
```

## Follow-up (not implemented)

- Per-source wall-clock budget in automation config.
- Split worker session from long-running scan session.
- Stale `RUNNING` automation run cleanup policy.
