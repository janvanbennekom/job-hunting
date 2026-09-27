# JobHunter deployment (Docker / Synology)

JobHunter runs as **disposable application containers** against **persistent PostgreSQL**
and optional mounted **automation JSON**. Streamlit and the scheduled worker share one
image; neither embeds a long-running scheduler loop.

## Components

| Component | Role |
|-----------|------|
| **web** | Streamlit dashboard (`8501`) |
| **worker** | One-shot `run_scheduled_pipeline.py --apply-if-due` (external schedule) |
| **db** (optional) | Bundled PostgreSQL 16 for self-contained installs |
| **migrate** (tools profile) | `python -m alembic upgrade head` — run explicitly, not on every start |

## Prerequisites

- Docker / Container Manager (Synology DSM 7+)
- Copy `.env.example` → `.env` (never commit `.env`)
- Copy `config/automation.example.json` → `config/automation.json` (gitignored locally)
- Set secrets: database, OpenAI, optional SMTP

## Environment variables

See `.env.example` for the full list. Required for production:

- `JOBHUNTER_DATABASE_URL` **or** `POSTGRES_*` components
- `JOBHUNTER_OPENAI_API_KEY`, `JOBHUNTER_OPENAI_MODEL` (production assessment)
- `JOBHUNTER_AUTOMATION_CONFIG` (container path, e.g. `/config/automation.json`)

Optional SMTP (when set, worker emails summaries instead of console-only):

- `JOBHUNTER_SMTP_HOST`, `JOBHUNTER_SMTP_PORT`
- `JOBHUNTER_SMTP_USER`, `JOBHUNTER_SMTP_PASSWORD`
- `JOBHUNTER_SMTP_FROM`, `JOBHUNTER_SMTP_TO`
- `JOBHUNTER_SMTP_USE_SSL` / `JOBHUNTER_SMTP_STARTTLS`

## PostgreSQL options

### A. Bundled database (compose default)

`docker compose` starts `db` with volume `jobhunter_pgdata`. Set `POSTGRES_PASSWORD`
(and optionally `POSTGRES_USER`, `POSTGRES_DB`) in `.env`. Application services use
`POSTGRES_HOST=db`.

### B. External / existing PostgreSQL

Set `JOBHUNTER_DATABASE_URL` to your instance (NAS IP, `host.docker.internal`, etc.).
Start only application services without the bundled DB, for example:

```bash
docker compose up -d web
```

Remove `depends_on: db` from `web` in a local override file if you do not run the
`db` service at all.

## Build

```bash
docker compose build
```

Image tag defaults to `jobhunter:local`.

## First deployment

1. Configure `.env` and `config/automation.json`.
2. Build the image.
3. **Run migrations once** (no auto-migrate on web/worker start):

   ```bash
   docker compose --profile tools run --rm migrate
   ```

   External DB only:

   ```bash
   docker compose run --rm --no-deps web python -m alembic upgrade head
   ```

4. Seed professional profile / search strategy if this is a fresh database (existing
   CLI seed scripts).
5. Start the dashboard:

   ```bash
   docker compose up -d web
   ```

6. Open `http://<host>:8501`.

## Upgrades

1. Pull/build the new image.
2. Run migrations once: `docker compose --profile tools run --rm migrate`
3. Recreate containers: `docker compose up -d web`

## Worker / scheduling (Synology)

The worker does **not** stay running. Schedule it externally.

**Recommended host frequency:** every **15 minutes** (or hourly). JobHunter’s
`--apply-if-due` only runs the pipeline when the configured weekday/time
(Europe/Amsterdam by default) matches the **current local minute**.

```bash
docker compose --profile worker run --rm worker
```

### Synology Task Scheduler

- Task type: User-defined script
- Schedule: every 15 minutes (example)
- Script:

```bash
cd /volume1/docker/job-hunter
/usr/local/bin/docker compose --profile worker run --rm worker
```

Adjust paths to your clone and Docker CLI location.

### Concurrency note

`--apply-if-due` matches a single clock minute. Avoid launching **two workers in the
same minute**; there is no distributed lock. A single scheduled task is sufficient.

When not due, the worker exits 0 immediately (`Schedule not due; skipping run.`) with
no source scans and no OpenAI calls.

## Automation configuration mount

Mount host `config/automation.json` read-only at `/config/automation.json` (see
`docker-compose.yml`). Tune `pipeline.production_assessment_enabled`, source limits,
and notifications without rebuilding the image.

## Notifications

- **Development / logs:** `ConsoleNotificationSender` (stdout → `docker logs`)
- **Production email:** configure SMTP env vars; worker uses `SmtpNotificationSender`

Two email types share SMTP when configured:

| Type | When | Notes |
|------|------|--------|
| Run summary | End of each applied worker run | Aggregated scan/ranking highlights; MEDIUM may appear here |
| HIGH opportunity alert | After ranking, per eligible new HIGH row | One message per `high_ranking:{ranking_id}`; no retroactive historical blast |

Set `JOBHUNTER_WEB_BASE_URL` (no trailing slash) so HIGH alerts can link to the
dashboard (`/?opportunity_id=…`). Toggle immediate HIGH alerts with
`notifications.high_ranking_alerts_enabled` in `config/automation.json`.
Failed HIGH sends are stored in `opportunity_notifications` and retried on later runs.

## Persistence

| Data | Location |
|------|----------|
| Opportunities, profile, strategy, assessments | PostgreSQL |
| Automation tuning | `config/automation.json` (host mount) |
| Container filesystem | Ephemeral |

Back up PostgreSQL regularly (`pg_dump` or volume snapshots).

## Troubleshooting

```bash
docker compose logs -f web
docker compose --profile worker run --rm worker python scripts/run_scheduled_pipeline.py --check-schedule
docker compose --profile worker run --rm worker python scripts/run_scheduled_pipeline.py --dry-run
```

Health: `curl http://localhost:8501/_stcore/health`

## Security

- Never bake API keys, DB passwords, or SMTP passwords into the image or compose file.
- Use `.env` on the host (gitignored) or Synology Docker secret UI.
- `.dockerignore` excludes `.env`, local automation JSON, and private profile PDFs.
