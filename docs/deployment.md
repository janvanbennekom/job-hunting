# JobHunter deployment (Docker / Synology)

JobHunter runs as **disposable application containers** against **persistent
PostgreSQL** (external server in production) and mounted **automation JSON**.
Streamlit and the scheduled worker share one image; neither embeds a long-running
scheduler loop.

Production on Synology exposes **only** an internal **edge** (Caddy) on
`localhost:8080`. DSM reverse proxy terminates HTTPS and forwards to the edge.
Streamlit is **not** published on port 8501.

## Components

| Component | Role |
|-----------|------|
| **edge** (production) | Caddy: `/` static landing, `/app/*` basic auth → Streamlit |
| **web** | Streamlit dashboard (`/app` base path in production) |
| **worker** | One-shot `run_scheduled_pipeline.py --apply-if-due` (Task Scheduler) |
| **migrate** (tools profile) | `python -m alembic upgrade head` — explicit only |
| **db** (dev only) | Bundled PostgreSQL 16 (`--profile bundled-db`) |

## A. NAS directory layout

Example:

```text
/volume1/docker/job-hunter/
├── .env                          # secrets (never commit)
├── config/
│   ├── automation.json           # pipeline tuning (gitignored)
├── deploy/landing/               # public static site (from Git)
├── deploy/caddy/Caddyfile
├── docker-compose.yml
└── docker-compose.prod.yml
```

## B. Clone / update

```bash
cd /volume1/docker
git clone <your-github-repo-url> job-hunter
cd job-hunter
git pull origin main
```

## C. Private files

1. Copy `.env.example` → `.env` and set production values (see below).
2. Copy `config/automation.example.json` → `config/automation.json`.
3. Set `JOBHUNTER_BASIC_AUTH_USER` and `JOBHUNTER_BASIC_AUTH_HASH` in `.env` (see below).

Never commit `.env` or `config/automation.json`.

### `config/automation.json` permissions (non-root container)

The application image runs as **`appuser` (UID 10001)**. The worker and web
containers mount `config/automation.json` read-only at `/config/automation.json`.
If the file is not readable by UID 10001, startup or worker runs fail with
`PermissionError`.

On the NAS (example paths):

```bash
cd /volume1/docker/job-hunter
chmod 755 config
chmod 644 config/automation.json
# Either ownership readable by UID 10001:
chown 10001:10001 config/automation.json
# Or keep your admin user but ensure world-read on the file and traverse on config/
```

Do **not** run the application container as root to work around permissions.

## D. Build (production)

```bash
cd /volume1/docker/job-hunter
docker compose -f docker-compose.prod.yml build
```

## E. Migration (production)

Requires `JOBHUNTER_DATABASE_URL` in `.env` pointing at the **existing external**
PostgreSQL server. Do **not** start the bundled `db` service on Synology.

```bash
docker compose -f docker-compose.prod.yml --profile tools run --rm migrate
```

## F. Start web stack (production)

```bash
docker compose -f docker-compose.prod.yml up -d web edge
```

## G. Verify containers

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f edge
```

## H. Verify landing locally (on the NAS)

```bash
curl -sS http://127.0.0.1:8080/ | head
curl -sS http://127.0.0.1:8080/health
```

Expect HTML for `/` and `ok` for `/health`. `/app/` prompts for HTTP basic auth
(email + password) before Streamlit.

## I. DSM reverse proxy

**Control Panel → Login Portal → Advanced → Reverse Proxy**

| Field | Value |
|--------|--------|
| Source protocol | HTTPS |
| Source hostname | `jobhunter.jvbgis.com` |
| Source port | `443` |
| Destination protocol | HTTP |
| Destination hostname | `localhost` |
| Destination port | `8080` |

Enable **WebSocket** for the source (required for Streamlit). Without this, the UI
often stays on a grey skeleton and feels very slow.

Optional **custom request headers** on the same reverse proxy rule (if DSM offers them):

| Header | Value |
|--------|--------|
| `X-Forwarded-Proto` | `https` |
| `X-Forwarded-Host` | `jobhunter.jvbgis.com` |
| `X-Forwarded-Port` | `443` |

Assign a **valid certificate** for `jobhunter.jvbgis.com` (Let's Encrypt). A browser
"Not secure" warning does not always block Streamlit, but fix it for production.

Enable HTTP → HTTPS redirect for the hostname.

Custom headers (if offered): forward `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`.

## J. Certificate

Use **Control Panel → Security → Certificate** to obtain a Let's Encrypt
certificate for `jobhunter.jvbgis.com` and assign it to the reverse proxy
entry and DSM services as needed.

## K. DNS (manual)

Create an **A** record:

```text
jobhunter.jvbgis.com  →  <Synology public IP>
```

JobHunter does not modify DNS.

## L. Firewall

Public internet needs **HTTPS (443)** to the Synology only.

Do **not** expose:

- `8501` (Streamlit)
- `5432` (PostgreSQL)
- `8080` on the WAN (bind edge to `127.0.0.1` only; DSM proxy uses localhost)

Restrict PostgreSQL firewall rules to the NAS (and admin workstations).

## M. Task Scheduler (worker)

**Recommended frequency:** every **15 minutes** (compatible with internal schedule logic).

Internal schedule: Monday and Thursday **from 08:00** Europe/Amsterdam. The worker
does **not** require the external task to fire at exactly 08:00: any poll **on or
after** 08:00 on a configured weekday may start a run. A second scheduled run the
same local calendar day is suppressed using persisted `AutomationRun` rows
(`trigger_type=SCHEDULED`, status SUCCESS or PARTIAL). The PostgreSQL advisory
lock still prevents overlapping workers.

| Setting | Value |
|---------|--------|
| Task type | Scheduled → **User-defined script** |
| User | An account that can run `sudo docker` (often `root` or admin) |
| Working directory | `/volume1/docker/job-hunter` |

Script (one line or use `bash -c`):

```bash
cd /volume1/docker/job-hunter && /usr/local/bin/docker compose -f docker-compose.prod.yml --profile worker run --rm worker
```

The worker container runs `python scripts/run_scheduled_pipeline.py --apply-if-due`,
exits when not due (no scans, no OpenAI), and uses a PostgreSQL advisory lock when
a run is due.

**Logs:** Task Scheduler history in DSM; container stdout:

```bash
sudo docker compose -f docker-compose.prod.yml --profile worker run --rm worker
```

After a due apply run with `notifications.enabled: true`, stdout should include
notification delivery markers (no secrets):

```text
Notification sender: SmtpNotificationSender
Sending automation summary via SmtpNotificationSender...
Automation summary sent successfully.
```

If the summary is not sent, look for an explicit skip line (`dry-run`,
`notifications disabled`, or `no notification sender`) instead of the success line.

**When not due** (typical off-window poll): stdout is only:

```text
Schedule not due; skipping run.
```

(exit code 0; no scans, OpenAI, or email).

**DSM settings:** enable **Send run details to DSM** (or equivalent) so stdout is
retained in Task Scheduler history. Run the task as a user that can execute
`sudo docker` (often `admin` / `root`).

**Disable safely:** disable or delete the DSM scheduled task (stack keeps running).

**Manual verification (immediate, not schedule-gated):**

```bash
cd /volume1/docker/job-hunter
sudo docker compose -f docker-compose.prod.yml --profile worker run --rm worker \
  python scripts/run_scheduled_pipeline.py --apply --trigger manual
```

Use small `limit` values in `config/automation.json` for a first live run. Existing
production assessments are reused when the input digest is unchanged (no extra OpenAI
call). Prefer `--dry-run` first to validate configuration without persisting.

**Schedule check only:**

```bash
sudo docker compose -f docker-compose.prod.yml --profile worker run --rm worker \
  python scripts/run_scheduled_pipeline.py --check-schedule
```

Adjust `docker` / `docker compose` paths for your DSM install (`which docker`).

## N. Upgrade procedure

```bash
cd /volume1/docker/job-hunter
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml --profile tools run --rm migrate
docker compose -f docker-compose.prod.yml up -d web edge
```

## O. Rollback / recovery

1. Check out a known-good Git commit or pull previous image tag.
2. Rebuild and run migrations if schema changed forward-only.
3. Restart `web`, `edge`.
4. Worker continues via Task Scheduler; no data loss if PostgreSQL is intact.

Full recovery: clone repository, restore `.env`, `automation.json`,
restore PostgreSQL from backup, build, migrate, start stack, recreate Task Scheduler.

---

## Environment variables

See `.env.example`. Production essentials:

| Variable | Purpose |
|----------|---------|
| `JOBHUNTER_ENV` | `production` |
| `JOBHUNTER_DATABASE_URL` | External PostgreSQL |
| `JOBHUNTER_OPENAI_*` | Production assessment |
| `JOBHUNTER_AUTOMATION_CONFIG` | `/config/automation.json` in container |
| `JOBHUNTER_SMTP_*` | Required when notifications enabled |
| `JOBHUNTER_WEB_BASE_URL` | `https://jobhunter.jvbgis.com` (alert links add `/app`) |
| `JOBHUNTER_BASIC_AUTH_USER` | Login name (your email) |
| `JOBHUNTER_BASIC_AUTH_HASH` | Bcrypt hash of your password (not plaintext) |

### HTTP basic auth (`/app`)

Caddy validates login before traffic reaches Streamlit. **Do not put the plaintext
password in `.env`** — store a bcrypt hash:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'choose-a-strong-password'
```

Add to `.env`:

```env
JOBHUNTER_BASIC_AUTH_USER=you@example.com
JOBHUNTER_BASIC_AUTH_HASH=<paste hash from command above>
```

**Synology / Docker Compose:** bcrypt hashes contain `$`. In `.env`, **double every
`$`** in the hash (example: `$2a$14$abc` → `$$2a$$14$$abc`). Otherwise Compose
warns about missing variables and Caddy gets a broken hash.

The browser will prompt for user/password when you open `/app/`. Use the same email
and the **plaintext** password (Caddy checks it against the hash).

### SMTP (production)

When `JOBHUNTER_ENV=production` and automation notifications or HIGH alerts are
enabled, the worker **requires** SMTP (no silent console fallback):

- `JOBHUNTER_SMTP_HOST`
- `JOBHUNTER_SMTP_PORT`
- `JOBHUNTER_SMTP_FROM`
- `JOBHUNTER_SMTP_TO`
- `JOBHUNTER_SMTP_USER` / `JOBHUNTER_SMTP_PASSWORD` (when AUTH required)
- `JOBHUNTER_SMTP_STARTTLS` or `JOBHUNTER_SMTP_USE_SSL`

**SMTP test (no scan, no OpenAI):**

```bash
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps web \
  python scripts/test_smtp_notification.py --dry-run
sudo docker compose -f docker-compose.prod.yml run --rm --no-deps web \
  python scripts/test_smtp_notification.py
```

HIGH-band alerts use the same SMTP transport when a new production HIGH ranking
occurs during a worker run. Policy details are in `docs/architecture.md` §25.

---

## PostgreSQL options

### Production (Synology)

Use **external PostgreSQL only**. Set `JOBHUNTER_DATABASE_URL`. Production
compose (`docker-compose.prod.yml`) does not define a `db` service.

### Local development (bundled database)

```bash
docker compose --profile bundled-db up -d db
docker compose --profile bundled-db --profile tools run --rm migrate
docker compose --profile bundled-db up -d web
```

---

## Notifications

| Type | When |
|------|------|
| Run summary | End of applied worker run |
| HIGH opportunity alert | New production HIGH ranking (`opportunity_notifications` audit) |

Toggle HIGH alerts: `notifications.high_ranking_alerts_enabled` in
`config/automation.json`.

---

## Backup / recovery (minimum)

| Asset | Method |
|-------|--------|
| PostgreSQL | Scheduled `pg_dump` (off-NAS encrypted copy) |
| `.env` | Encrypted backup / password manager |
| `config/automation.json` | Copy with secrets |

Application containers need **no** persistent volumes in production.

Example dump (run where `pg_dump` can reach the DB):

```bash
pg_dump "$JOBHUNTER_DATABASE_URL" -Fc -f jobhunter-$(date +%Y%m%d).dump
```

---

## Troubleshooting

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml \
  --profile worker run --rm worker python scripts/run_scheduled_pipeline.py --check-schedule
```

Edge health: `curl http://127.0.0.1:8080/health`

Streamlit (internal): `docker compose ... exec web curl -fsS http://127.0.0.1:8501/app/_stcore/health`

## Security

- Never bake API keys, DB passwords, SMTP passwords, or basic-auth hashes into images.
- Use `.env` on the NAS (gitignored).
- Streamlit is reachable only on the Docker internal network; `/app` is gated by Caddy basic auth.
- `.dockerignore` excludes `.env`, automation JSON, and private profile PDFs.

## Production go-live checklist

| # | Item | How to verify |
|---|------|----------------|
| 1 | Docker stack running | `docker compose -f docker-compose.prod.yml ps` — `web`, `edge` healthy |
| 2 | Landing page | `https://jobhunter.jvbgis.com/` or `curl http://127.0.0.1:8080/` |
| 3 | `/app` protected | Basic auth prompt; no anonymous Streamlit |
| 4 | Streamlit WebSocket | Browser devtools: `wss://…/app/_stcore/stream` → **101** |
| 5 | Public TLS | Valid cert for `jobhunter.jvbgis.com` in DSM (client VPN tools may warn) |
| 6 | External PostgreSQL | Worker/web start; migrate succeeds |
| 7 | Alembic at head | `20260927_0013` after migrate |
| 8 | OpenAI production | `JOBHUNTER_OPENAI_*` in `.env`; `production_assessment_enabled` in automation JSON |
| 9 | SMTP | `scripts/test_smtp_notification.py` succeeds |
| 10 | HIGH alert policy | Unit tests; live email only on new HIGH ranking during worker |
| 11 | Manual worker | `--apply --trigger manual` with small limits |
| 12 | AutomationRun audit | Row in DB after worker |
| 13 | Task Scheduler | Every 15 min; command in section M |
| 14 | `JOBHUNTER_WEB_BASE_URL` | `https://jobhunter.jvbgis.com` |
| 15 | Router/firewall | **443** to NAS only; not 8501/5432/8080 on WAN |
| 16 | No public Streamlit/DB ports | `edge` bind `127.0.0.1` unless LAN debug |
| 17 | Secrets not in Git | `.env`, `automation.json` gitignored |
| 18 | Backup | `pg_dump`, `.env`, `automation.json` per backup section |
