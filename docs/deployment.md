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
| **edge** (production) | Caddy: `/` static landing, `/app/*` → oauth2-proxy |
| **oauth2-proxy** (production) | OIDC login, allowed-email gate, upstream to Streamlit |
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
│   └── oauth2-proxy/
│       └── allowed_emails.txt    # authorised users (gitignored)
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
3. Create allowed-email list:

   ```bash
   mkdir -p config/oauth2-proxy
   cp config/oauth2-proxy.allowed_emails.example.txt config/oauth2-proxy/allowed_emails.txt
   # Edit: one authorised email per line
   ```

Never commit `.env`, `config/automation.json`, or `allowed_emails.txt`.

## D. Build (production)

```bash
cd /volume1/docker/job-hunter
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

## E. Migration (production)

Requires `JOBHUNTER_DATABASE_URL` in `.env` pointing at the **existing external**
PostgreSQL server. Do **not** start the bundled `db` service on Synology.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile tools run --rm migrate
```

## F. Start web stack (production)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d web oauth2-proxy edge
```

## G. Verify containers

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f edge
```

## H. Verify landing locally (on the NAS)

```bash
curl -sS http://127.0.0.1:8080/ | head
curl -sS http://127.0.0.1:8080/health
```

Expect HTML for `/` and `ok` for `/health`. `/app/` should redirect to OAuth when
not authenticated (once oauth2-proxy is configured).

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

Enable **WebSocket** for the source (required for Streamlit).

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

**Recommended frequency:** every **15 minutes**.

Internal pipeline schedule (unchanged): Monday and Thursday 08:00
Europe/Amsterdam via `--apply-if-due`.

Task type: **Scheduled** → **User-defined script**

```bash
cd /volume1/docker/job-hunter
/usr/local/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile worker run --rm worker
```

Adjust `docker` / `docker compose` paths for your DSM install.

The worker runs independently of the web UI and holds a PostgreSQL advisory
lock during `--apply` so a second concurrent worker skips safely.

## N. Upgrade procedure

```bash
cd /volume1/docker/job-hunter
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile tools run --rm migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d web oauth2-proxy edge
```

## O. Rollback / recovery

1. Check out a known-good Git commit or pull previous image tag.
2. Rebuild and run migrations if schema changed forward-only.
3. Restart `web`, `oauth2-proxy`, `edge`.
4. Worker continues via Task Scheduler; no data loss if PostgreSQL is intact.

Full recovery: clone repository, restore `.env`, `automation.json`, OAuth files,
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
| `OAUTH2_PROXY_*` | OAuth client, cookie secret, redirect URL |

### SMTP (production)

When `JOBHUNTER_ENV=production` and automation notifications or HIGH alerts are
enabled, the worker **requires** SMTP (no silent console fallback):

- `JOBHUNTER_SMTP_HOST`
- `JOBHUNTER_SMTP_PORT`
- `JOBHUNTER_SMTP_FROM`
- `JOBHUNTER_SMTP_TO`
- `JOBHUNTER_SMTP_USER` / `JOBHUNTER_SMTP_PASSWORD` (when AUTH required)
- `JOBHUNTER_SMTP_STARTTLS` or `JOBHUNTER_SMTP_USE_SSL`

### OAuth2-proxy setup

1. Register an OAuth application with your provider (Google, GitHub, Microsoft, or generic OIDC).
2. Set authorised redirect URI to  
   `https://jobhunter.jvbgis.com/app/oauth2/callback`
3. In `.env` set at minimum:
   - `OAUTH2_PROXY_PROVIDER` (e.g. `google`)
   - `OAUTH2_PROXY_CLIENT_ID`
   - `OAUTH2_PROXY_CLIENT_SECRET`
   - `OAUTH2_PROXY_COOKIE_SECRET` (generate: `openssl rand -base64 32`)
   - `OAUTH2_PROXY_REDIRECT_URL` (URL above)
4. List allowed emails in `config/oauth2-proxy/allowed_emails.txt`.

Logout: use oauth2-proxy sign-out (`/app/oauth2/sign_out` by default).

---

## PostgreSQL options

### Production (Synology)

Use **external PostgreSQL only**. Set `JOBHUNTER_DATABASE_URL`. Do not enable
`--profile bundled-db` with `docker-compose.prod.yml`.

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
| `config/oauth2-proxy/allowed_emails.txt` | Copy |
| OAuth client secret | Provider console + `.env` backup |

Application containers need **no** persistent volumes in production.

Example dump (run where `pg_dump` can reach the DB):

```bash
pg_dump "$JOBHUNTER_DATABASE_URL" -Fc -f jobhunter-$(date +%Y%m%d).dump
```

---

## Troubleshooting

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile worker run --rm worker python scripts/run_scheduled_pipeline.py --check-schedule
```

Edge health: `curl http://127.0.0.1:8080/health`

Streamlit (internal): `docker compose ... exec web curl -fsS http://127.0.0.1:8501/app/_stcore/health`

## Security

- Never bake API keys, DB passwords, SMTP passwords, or OAuth secrets into images.
- Use `.env` on the NAS (gitignored).
- Streamlit is reachable only on the Docker internal network and via oauth2-proxy.
- `.dockerignore` excludes `.env`, automation JSON, and private profile PDFs.
