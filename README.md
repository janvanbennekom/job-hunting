# Job Hunting AI Agent (JobHunter)

Personal AI-assisted discovery, assessment, and application support for
international consulting and specialist opportunities aligned with a defined
professional profile and search strategy.

Governance and design authority:

- [AGENTS.md](AGENTS.md) — agent and engineering principles
- [docs/architecture.md](docs/architecture.md) — system architecture
- [docs/implementation-plan.md](docs/implementation-plan.md) — phased implementation plan

## Current scope (Bootcamp MVP)

Development follows the implementation plan incrementally through phased
delivery. The Bootcamp MVP vertical slice (Phases 0–10) covers one real
source through acquire → normalize → persist → filter → AI matching → rank →
Streamlit dashboard and human review.

## Repository structure

```
job-hunting/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── docs/
├── src/jobhunter/          # importable package (src layout)
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   ├── connectors/
│   ├── ai/
│   └── ui/
├── tests/
├── data/fixtures/
└── scripts/
```

## Local development

Requires **Python 3.11+**.

Create a virtual environment, install the package with development dependencies,
and copy environment placeholders:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Configuration is read from environment variables (see `.env.example`). Load
`.env` into your shell or use your IDE’s env-file support; the application does
not use `python-dotenv`.

### PostgreSQL

A local PostgreSQL database is required for persistence development and
integration tests. Configure either:

- `JOBHUNTER_DATABASE_URL` (`postgresql+psycopg://…`), or
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and
  `POSTGRES_PASSWORD`.

Apply schema migrations:

```powershell
alembic upgrade head
```

### Docker / Synology deployment

Production packaging uses a **single image** for Streamlit and the scheduled
worker. See [docs/deployment.md](docs/deployment.md) for build, migrations,
environment variables, SMTP notifications, and Synology Task Scheduler setup.

Quick start (bundled PostgreSQL):

**External PostgreSQL** (e.g. `db.jvbgis.com`) — set `JOBHUNTER_DATABASE_URL` in `.env`:

```powershell
Copy-Item config/automation.example.json config/automation.json
docker compose build
docker compose --profile tools run --rm migrate
docker compose up -d web
```

**Bundled PostgreSQL** in Docker (optional):

```powershell
Copy-Item .env.example .env
# Set POSTGRES_PASSWORD in .env
Copy-Item config/automation.example.json config/automation.json
docker compose -f docker-compose.yml -f docker-compose.bundled-db.yml build
docker compose -f docker-compose.yml -f docker-compose.bundled-db.yml --profile bundled-db up -d db
docker compose -f docker-compose.yml -f docker-compose.bundled-db.yml --profile bundled-db --profile tools run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.bundled-db.yml --profile bundled-db up -d web
```

Synology production (external PostgreSQL, Caddy basic auth, public landing) uses
`docker compose -f docker-compose.prod.yml` — see [docs/deployment.md](docs/deployment.md).

### Project spreadsheet import (Phase 3C.1)

Import structured project/capability data from the local XLSX workbook (dry-run
by default; does not print database credentials):

```powershell
python scripts/import_project_spreadsheet.py --source "docs/2 model_instances - postgres.xlsx"
python scripts/import_project_spreadsheet.py --source "docs/2 model_instances - postgres.xlsx" --apply
```

To replace spreadsheet-owned assignments after a change to assignment identity
rules, purge assignment rows for that source and re-import (capabilities and
ProfileDocument are kept):

```powershell
python scripts/import_project_spreadsheet.py --source "docs/2 model_instances - postgres.xlsx" --purge-spreadsheet-assignments --apply
```

### Professional Services seed (Phase 3C.2)

Load curated service definitions from JSON (dry-run by default):

```powershell
python scripts/seed_professional_services.py
python scripts/seed_professional_services.py --apply
```

### CV profile seed (Phase 3C.3B)

Load curated CV-derived skills, languages and countries from JSON (dry-run by
default):

```powershell
python scripts/seed_cv_profile.py
python scripts/seed_cv_profile.py --apply
```

### Search strategy seed (Phase 4B)

Load curated search strategy from JSON (dry-run by default):

```powershell
python scripts/seed_search_strategy.py
python scripts/seed_search_strategy.py --apply
```

Optional logging setup in code:

```python
from jobhunter.infrastructure.logging_config import configure_logging

configure_logging()
```

### Opportunity eligibility (Phase 7)

Evaluate persisted opportunities against the active search strategy revision:

```powershell
python scripts/evaluate_opportunity_eligibility.py --source-id fao-external-jobs
```

Source scans (`--apply`, e.g. FAO or DevelopmentAid) run Phase 7 automatically after Phase 5 processing.

### Profile / relevance assessment (Phase 8)

Assess opportunities with grounded AI structured output. The CLI defaults to
**OpenAI** and requires `JOBHUNTER_OPENAI_API_KEY` and `JOBHUNTER_OPENAI_MODEL`.
It does not silently use a fake model. For explicit local/dev runs only:

```powershell
python scripts/assess_opportunity_profile.py --source-id fao-external-jobs
python scripts/assess_opportunity_profile.py --source-id fao-external-jobs --provider fake
```

Automated tests inject `FakeAssessmentModel` directly. Source scans (`--apply`) run
Phase 8 after Phase 7 only when OpenAI is configured; unchanged opportunities
reuse prior successful assessments.

### Opportunity ranking (Phase 9)

Deterministic prioritisation from Phase 8 assessments and active search strategy
(no AI ranking call):

```powershell
python scripts/rank_opportunities.py --source-id fao-external-jobs
```

Production ranking requires OpenAI-backed assessments. Development only:

```powershell
python scripts/rank_opportunities.py --source-id fao-external-jobs --include-fake-assessments
```

### Dashboard (Phase 10)

Review opportunities, assessments, rankings, and human review decisions
(requires PostgreSQL, migrations, and configured `.env`):

```powershell
streamlit run src/jobhunter/ui/streamlit/app.py
```

Production views exclude `model_provider=fake` assessments and fake-derived
rankings unless you enable the sidebar development toggle.

### Application tracking (Phase 14)

Track consultancy pursuit **after** you decide to pursue an opportunity (separate
from review triage SHORTLIST / INVESTIGATE / DISMISS). Use **Start pursuing** on
opportunity detail or the **Applications** work queue. Requires Alembic revision
`20260928_0014`.

### Search strategy (Phase 11 + Phase 15)

The **Search strategy** page shows themes, criteria, and exclusions in
structured tables. Change strategy in two ways (both create a new immutable
revision only after you confirm a diff):

1. **Structured edit** — deterministic field changes (no LLM).
2. **Request a change** — natural language interpreted by OpenAI or the
   explicit fake provider for development.

Operational source limits and keywords are **not** strategy revisions; see
**Sources** and `config/automation.json`.

### Operator UI (Phase 15)

- **Home** — lifecycle, eligibility, and ranking summaries as tables; click a
  count to open **Opportunities** with the matching filter.
- **Opportunities** / **Applications** — open opportunity detail without
  entering UUIDs; deep links:
  `…/app/opportunity_detail?opportunity_id=<uuid>`.
- **Sources** — registry-driven scan status and `automation.json` acquisition
  settings (read-only in UI; edit the file on the deployment host).

HIGH-ranking email alerts use `JOBHUNTER_WEB_BASE_URL` for the same detail
links when configured.

### Source expansion (Phase 17A–17B)

Research: [docs/source-expansion-analysis.md](docs/source-expansion-analysis.md).

**Phase 17B connectors** (automation keys `worldbank`, `undp`, `afdb`) use the same
scan → Phase 5 → Phase 7 pipeline as FAO and DevelopmentAid. Enable them in
`config/automation.json` (see `config/automation.example.json`). Recommended first
production `limit`: **10** per new source, then increase after verifying counts and
description quality.

Optional live smoke tests: `tests/connectors/test_worldbank_live.py`,
`test_undp_live.py`, `test_afdb_live.py` (`pytest -m live`).

### Core operator experience (Phase 16)

Opportunity detail shows structured eligibility, assessment, and ranking
sections with human-readable labels. Assessment states are explicit (not
assessed, fake-only, failed, limited source data, etc.). Full assessment JSON
is available only as a collapsed diagnostic view when a payload exists.
Structured strategy editing includes preference criteria and hard constraints.

### FAO Jobs scan (Phase 6)

Acquire vacancies from [FAO Jobs](https://jobs.fao.org/careersection/fao_external/jobsearch.ftl)
and persist them through the Phase 5 pipeline (requires PostgreSQL and migrations):

```powershell
# Inspect retrieval/mapping without database writes
python scripts/scan_fao_jobs.py --dry-run --limit 5 --keyword "GIS"

# Persist a small sample (recommended for first run)
python scripts/scan_fao_jobs.py --apply --limit 5 --keyword "land"
```

Optional live smoke test (not part of default pytest):

```powershell
pytest -m live tests/connectors/test_fao_live.py
```

### Scheduled pipeline / worker (Phase 13)

Run the full multi-source pipeline once (acquire → Phase 5 → Phase 7 → optional
Phase 8 → optional Phase 9 → HIGH alert evaluation → run summary notification).
Intended for cron, Synology Task Scheduler, or Docker worker — not for Streamlit.

Immediate email/console alerts are sent only for **new** production **HIGH**
rankings (see `docs/architecture.md` §25). Set `JOBHUNTER_WEB_BASE_URL` for
dashboard links in those emails.

Copy `config/automation.example.json` to `config/automation.json` (or set
`JOBHUNTER_AUTOMATION_CONFIG`) to adjust schedule semantics, enabled sources,
limits, and whether production OpenAI assessment / ranking / notifications run.

```powershell
# Safe preview (no SourceScans, opportunities, assessments, rankings, or automation_runs)
python scripts/run_scheduled_pipeline.py --dry-run

# Manual one-shot run (persists; console notification when enabled)
python scripts/run_scheduled_pipeline.py --apply

# External scheduler: run only when schedule is due (Europe/Amsterdam weekday/time)
python scripts/run_scheduled_pipeline.py --apply-if-due
```

Production automation never uses `FakeAssessmentModel`. Enable OpenAI in config
(`pipeline.production_assessment_enabled`) only when `JOBHUNTER_OPENAI_*` is set.

### DevelopmentAid Jobs scan (Phase 12)

Acquire vacancies from [DevelopmentAid job search](https://www.developmentaid.org/jobs/search)
via the public frontend JSON API and the same downstream pipeline as FAO:

```powershell
python scripts/scan_developmentaid_jobs.py --dry-run --limit 5 --keyword "GIS"
python scripts/scan_developmentaid_jobs.py --apply --limit 8 --keyword "land administration"
```

Use `--no-details` to skip per-job detail fetches (list summaries only).

With `fetch_details: true`, detail GETs are **sequential** and throttled (~3s apart)
with bounded **HTTP 429** retries (see `docs/deployment.md`). List data is kept
if some details fail (`PARTIAL` scan). Full detail responses map sectors, languages,
experience, organisation type, contract type, and external application URLs into
source-neutral `structured_facts` for assessment and the opportunity detail UI
(anonymous API only — no DevelopmentAid login).

Optional live smoke test:

```powershell
pytest -m live tests/connectors/test_developmentaid_live.py
```

### Opportunity processing fixtures (Phase 5)

Exercise the processing pipeline against representative JSON (requires
PostgreSQL and migrations). Use `--dry-run` to validate fixture parsing only:

```powershell
python scripts/process_fixture_opportunities.py --dry-run
python scripts/process_fixture_opportunities.py --fixture data/fixtures/opportunities/sample_raw_sequence.json
```

Integration tests cover the same pipeline with transaction rollback and do not
require seeding opportunities into long-lived data.

## Tests

Unit tests (domain and configuration):

```powershell
pytest -m "not integration"
```

Include PostgreSQL integration tests (requires database configuration and
migrations applied):

```powershell
pytest
```

Verify import:

```powershell
python -c "import jobhunter; print(jobhunter.__version__)"
```
