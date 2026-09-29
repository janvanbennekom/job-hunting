# Source expansion analysis (Phase 17A)

**Investigation date:** 2026-09-29  
**Purpose:** Inform Phase 17B connector implementation — research only, no code changes.  
**Baseline connectors:** FAO (Oracle Taleo JSON), DevelopmentAid (public frontend JSON).

---

## 1. Existing connector contract (JobHunter)

### Pipeline shape

```
SourceScanAdapter (automation) → *ScanService → Connector → RawOpportunity[]
    → OpportunityProcessingService (+ source-specific Normalizer)
    → eligibility → (optional) assessment → ranking
```

Each source registers:

- `KNOWN_SOURCE_KEYS` + `SOURCE_KEY_TO_JOB_SOURCE_ID` in `infrastructure/automation/config.py`
- `application/sources/registry.py` (UI metadata)
- `SourceScanAdapter` in `application/automation/source_adapters.py`
- Dedicated `*ScanService` (today: `FaoScanService`, `DevelopmentAidScanService`)
- Package under `connectors/<name>/`: `client`, `connector`, `mapper`, `normalizer`, `identity`

### RawOpportunity minimum contract

| Field | Requirement |
|-------|-------------|
| `source_id` | Stable `JobSource.id` (e.g. `fao-external-jobs`) |
| `retrieved_at` | Timezone-aware UTC |
| `source_reference` | **Strongly required** — per-source stable ID for idempotency (`(source_id, source_reference)` in processing) |
| `source_url` | Canonical human URL for verification |
| `raw_title` | Required for useful processing |
| `raw_organisation` | Valuable (client/donor) |
| `raw_location` | Valuable |
| `raw_deadline` | String as published; normalizer parses |
| `raw_description` | Drives Phase 8 sufficiency (`infer_source_data_sufficiency`) |
| `extra` | Source-specific fields (FAO: `jobId`, `contestNo`, columns JSON) |

### Behavioural expectations

1. **Errors:** Map/parse failures per record → collect errors; do not abort entire scan (FAO/DevelopmentAid pattern).
2. **Idempotency:** Re-scan same `source_reference` → observation reuse / material change detection, not duplicate opportunities.
3. **Pagination:** Connector respects `limit` from `SourceAutomationConfig`; polite page loops.
4. **Detail fetch:** Optional second step (DevelopmentAid `fetch_details`); FAO list payload is summary-oriented.
5. **Tests:** Saved JSON fixtures; no live network in default pytest; optional `@pytest.mark.live`.
6. **Config:** `automation.json` entry: `key`, `enabled`, `keyword`, `limit`, optional `fetch_details` (schema is shared; unknown keys rejected today).

### Reference baselines

| | FAO | DevelopmentAid |
|---|-----|----------------|
| Access | PUBLIC_NO_AUTH (session cookie) | PUBLIC_NO_AUTH |
| Interface | Taleo REST `searchjobs` | POST search + GET detail |
| Detail quality | SUMMARY_ONLY (list columns) | FULL_DETAIL when `fetch_details` |
| Stable ID | `jobId` / `contestNo` | numeric `id` |
| Complexity | implemented | implemented |
| Stability | MEDIUM (undocumented but stable Taleo) | MEDIUM (frontend API) |

---

## 2. Candidate source matrix

| Source | Access | Interface | Detail quality | Stable ID | Individual consulting | Complexity | Stability risk | JobHunter value |
|--------|--------|-----------|----------------|-----------|----------------------|------------|----------------|-----------------|
| **FAO** (baseline) | PUBLIC_NO_AUTH | Taleo JSON | SUMMARY_ONLY | Yes (`jobId`) | Yes (staff + consultants) | implemented | MEDIUM | HIGH |
| **DevelopmentAid** (baseline) | PUBLIC_NO_AUTH | Frontend JSON | FULL_DETAIL* | Yes (`id`) | Yes | implemented | MEDIUM | VERY_HIGH |
| World Bank (project procurement) | PUBLIC_NO_AUTH | Documented REST `search.worldbank.org/api/v2/procnotices` | GOOD_STRUCTURED (`notice_text`) | Yes (`id` / notice id) | Mixed (EOI/QCBS; often firms) | LOW–MEDIUM | LOW | HIGH |
| World Bank (operational RFx Now) | ACCOUNT_REQUIRED | Vendor portal (WBGeProcure) | FULL_DETAIL | Yes (vendor-side) | Yes (IC) | HIGH | MEDIUM | HIGH (wrong channel for unattended) |
| UNDP | PUBLIC_NO_AUTH | Official RSS 1.0 + JSON feed toolkit | VARIABLE (feed-dependent) | Yes (vacancy id in feed) | Yes | LOW–MEDIUM | LOW–MEDIUM | VERY_HIGH |
| UNOPS | PUBLIC_NO_AUTH | HTML careers + `careers.unops.org` marketplace | GOOD_STRUCTURED on detail pages | Yes (vacancy id in URL) | Yes (ICA/retainer) | MEDIUM–HIGH | MEDIUM | HIGH |
| UN Careers (Inspira) | PUBLIC_NO_AUTH | SPA; per-opening JSON `…/opening/joV2/{id}/en` | FULL_DETAIL on detail API | Yes (`jobId`) | Mostly staff; some consultants | MEDIUM | MEDIUM–HIGH | MEDIUM |
| DevNetJobs | SUBSCRIPTION_REQUIRED / PUBLIC_NO_AUTH | Server HTML; no official API | GOOD_STRUCTURED on listings | Weak (listing id unclear) | Yes | HIGH | HIGH | MEDIUM |
| AfDB consultants | PUBLIC_NO_AUTH | HTML table + **RSS** (`…/consultants/rss/`) | GOOD_STRUCTURED (EOI pages) | Yes (EOI ref in table) | Yes (IC + firms) | MEDIUM | MEDIUM | HIGH |
| AfDB Fieldglass CMS | ACCOUNT_REQUIRED | SAP Fieldglass | FULL_DETAIL | Yes (posting id) | Yes | HIGH | MEDIUM | HIGH (portal not scrape target) |
| WFP (direct) | PUBLIC_NO_AUTH | Workday (`wday/cxs/…/jobs` POST) | PARTIAL list; FULL via JSON-LD on job page | Yes (`JR…` req id) | Mixed | MEDIUM–HIGH | MEDIUM–HIGH | HIGH |
| WFP / UN (via ReliefWeb) | PUBLIC_API_KEY† | Documented `api.reliefweb.int/v2/jobs` | FULL_DETAIL (`body` field) | Yes (`uuid`) | Yes (Consultancy type) | LOW–MEDIUM | LOW (API) | VERY_HIGH |
| EU / EC (TED) | PUBLIC_NO_AUTH | Documented POST `api.ted.europa.eu/v3/notices/search` | FULL_DETAIL (XML/HTML links) | Yes (notice id) | Mostly firm procurement | MEDIUM | LOW | MEDIUM |
| GIZ | ACCOUNT_REQUIRED / PUBLIC_NO_AUTH | `jobs.giz.de` career portal; fragmented OKV/country DBs | VARIABLE | Varies | Mixed (staff vs local consultant) | HIGH | MEDIUM | MEDIUM |
| IFAD staff/rosters | ACCOUNT_REQUIRED | `job.ifad.org` (eRecruit) | FULL_DETAIL on vacancies | Yes (vacancy id) | Rosters + staff | MEDIUM | MEDIUM | MEDIUM |
| IFAD project procurement | PUBLIC_NO_AUTH | HTML notices on `ifad.org` project procurement | GOOD_STRUCTURED | Yes (notice codes) | Firm + QCBS | MEDIUM | MEDIUM | MEDIUM |
| MCC partner country | AUTHENTICATED_BROWSER_ONLY | `mcc.dgmarket.com` (session cookie) | VARIABLE | Varies | Mixed | HIGH | HIGH | LOW–MEDIUM |
| ADB CSRN/CMS | ACCOUNT_REQUIRED | `csrn.adb.org` / `cms.adb.org` (public browse) | GOOD_STRUCTURED | Yes (CSRN id) | Yes | HIGH | MEDIUM | HIGH |

† ReliefWeb requires a **pre-approved `appname`** (free, request via reliefweb.int/contact since Nov 2025).

### Optional discoveries (not in original list)

| Source | Notes | Value |
|--------|-------|-------|
| **ReliefWeb Jobs** | Single API aggregates many UN/NGO postings (WFP, UNICEF, etc.) | VERY_HIGH as meta-source |
| **UNGM** | UN procurement notices; separate from agency job boards | MEDIUM (procurement not IC jobs) |
| **Impactpool** | Hosts many roster/EOI pages (IFAD, etc.) | LOW as primary (aggregator, not authoritative) |

---

## 3. Detailed findings by source

### 3.1 World Bank

**Two distinct channels:**

1. **Project procurement notices (borrower-administered)** — `GET https://search.worldbank.org/api/v2/procnotices?format=json&rows=&os=&qterm=`  
   - Verified 2026-09-29: JSON returns fields including `id`, `notice_type`, `submission_date`, `bid_description`, `notice_text`, `project_id`, country, method.  
   - **Access:** PUBLIC_NO_AUTH. **Stability:** LOW risk (documented open API).  
   - **Relevance:** EOIs, QCBS, consultancy services on bank-financed projects — high alignment with land/GIS/ICT consulting, often firm-oriented.  
   - **Phase 8:** `notice_text` → likely **ADEQUATE** or **PARTIAL**.

2. **Operational consulting (corporate procurement)** — **WBGeProcure RFx Now** replaced eConsultant2 (2023+).  
   - Vendor registration required; search inside authenticated portal. FAQ states no automatic notifications by country.  
   - **Access:** ACCOUNT_REQUIRED for meaningful search. **Not suitable** for unattended Synology worker without stored vendor credentials (out of scope / high risk).

### 3.2 UNDP

- Official **RSS 1.0** feeds: `https://jobs.undp.org/cj_rss_feed.cfm` (all vacancies, programmes, country offices).  
- UNDP **Web 2.0 JSON feed generator** documented at `public-components.undp.org/help/howto/jobs.cfm` (filter by office/region).  
- **Access:** PUBLIC_NO_AUTH. **Detail:** feed entries typically include title, link, dates, description snippet — **VARIABLE** to **GOOD_STRUCTURED**.  
- **IDs:** vacancy URLs/ids in feed items. **Filtering:** keyword via feed selection more than query params.

### 3.3 UNOPS

- Vacancies: legacy `jobs.unops.org` ASPX + newer `careers.unops.org/careersmarketplace/JobDetail/…/{id}`.  
- ICA/retainer consultancies appear in job categories (Procurement, Engineering, etc.).  
- **No documented public API** found. **Access:** PUBLIC_NO_AUTH for listing/detail HTML.  
- **Stable ID:** numeric id in URL (e.g. `2479`, `25849`). **Detail:** full job description on detail pages.

### 3.4 UN Careers (Inspira)

- Modern SPA; guessed REST paths under `/api/public/` returned HTML shell (routing).  
- Community documentation: detail endpoint pattern  
  `GET https://careers.un.org/api/public/opening/joV2/{jobId}/en` → structured JSON including `jobDescription` (no auth observed in public write-ups).  
- **List endpoint** not confirmed in this investigation — likely requires frontend network inspection or RSS (mentioned in community posts).  
- **Access:** PUBLIC_NO_AUTH for detail JSON if job id known; full crawl **MEDIUM–HIGH** risk (undocumented).  
- **Content:** mostly **P-staff**; filter by category/network needed to avoid irrelevant volume.

### 3.5 DevNetJobs

- `devnetjobs.org` — commercial board; premium email alerts; **no official API/RSS** authorized.  
- Third-party scraping reported but **HIGH** stability/ToS risk.  
- **Access:** PUBLIC_NO_AUTH for browsing; programmatic use **NOT_CURRENTLY_RECOMMENDED**.

### 3.6 African Development Bank (AfDB)

- **Consultant vacancy table** + link to SAP Fieldglass CMS (`afdb1.fcp.eu.fieldglass.cloud.sap`).  
- **RSS:** `https://www.afdb.org/en/about-us/careers/current-vacancies/consultants/rss/` (advertised on consultants page).  
- Separate legacy **E-Consultant/DACON** registration (`econsultant.afdb.org`) — registration database, not a vacancy feed.  
- **Access:** PUBLIC_NO_AUTH for RSS/HTML listings; apply via Fieldglass needs account.  
- **IDs:** EOI titles with publication/closing dates in table; detail pages per row.

### 3.7 WFP

- Careers on **Workday**: `wfp.wd3.myworkdayjobs.com` — public POST `…/wday/cxs/wfp/…/jobs` pattern (undocumented, used by many scrapers).  
- List payload: title, location, `externalPath`, requisition id; **detail** via job page JSON-LD `JobPosting`.  
- **Alternative:** ReliefWeb lists WFP consultancies with structured `body` (filter org = WFP).  
- **Access:** PUBLIC_NO_AUTH; **Stability:** MEDIUM (Workday).

### 3.8 European Union / European Commission (TED)

- **TED Search API v3:** `POST https://api.ted.europa.eu/v3/notices/search` — expert query, pagination, anonymous access (API key optional for rate limits).  
- Official docs: `docs.ted.europa.eu`.  
- **Content:** procurement notices (CPV-coded), mostly **contracts to firms**; expert/individual assignments are a subset.  
- **Volume:** very large — requires strict query/limit strategy. **Phase 8:** often **ADEQUATE** where description present.

### 3.9 GIZ

- International vacancies: `jobs.giz.de` (registration for applications).  
- **Local consultant / OKV** and country-specific enlistment sites (e.g. Bangladesh) — not a single global vacancy API.  
- **Access:** mixed PUBLIC browse, ACCOUNT for applications. **Complexity:** HIGH fragmentation.

### 3.10 IFAD

- Staff/rosters: `job.ifad.org` (eRecruit); roster calls on Impactpool mirror official posts.  
- **Project procurement notices** on `ifad.org/en/project-procurement/opportunities` (GPN/SPN/CAN HTML).  
- **Access:** PUBLIC_NO_AUTH for procurement notices; vacancies may need portal interaction.  
- **Land sector relevance:** MEDIUM–HIGH (agriculture/rural, some land/GIS).

### 3.11 Millennium Challenge Corporation (MCC)

- Partner-country opportunities on **dgMarket** (`mcc.dgmarket.com`) — requires `digi_session_id` cookie (session).  
- Quarterly **Business Forecast** PDF/HTML on mcc.gov (planning, not live feed).  
- HQ contracts via SAM.gov (US federal).  
- **Access:** AUTHENTICATED_BROWSER_ONLY / awkward for automation. **Value:** LOW–MEDIUM for Jan’s profile.

### 3.12 Asian Development Bank (ADB)

- **CSRN** public search: `csrn.adb.org`; registered consultants use `cms.adb.org`.  
- No public API for CSRNs (ADB “projects API” is project metadata only).  
- **Access:** PUBLIC_NO_AUTH to browse CSRN; proposals require CMS account.  
- **Detail:** GOOD on CSRN pages. **Complexity:** HIGH for unattended end-to-end.

---

## 4. Authentication summary

| Class | Sources | Synology unattended implication |
|-------|---------|--------------------------------|
| PUBLIC_NO_AUTH | WB procnotices, UNDP RSS/JSON, AfDB RSS, TED, ReliefWeb†, FAO, DevelopmentAid | Suitable with polite rate limits |
| PUBLIC_API_KEY | ReliefWeb (`appname`) | Suitable after one-time approval |
| ACCOUNT_REQUIRED | WB RFx Now, ADB CMS, AfDB Fieldglass apply, GIZ apply | Not suitable without credential vaulting |
| AUTHENTICATED_BROWSER_ONLY | MCC dgMarket | Defer |
| NOT_PROGRAMMATICALLY_ACCESSIBLE | DevNetJobs (no sanctioned API) | Defer |

---

## 5. Filtering and recall

JobHunter strategy: **broad acquisition → eligibility → AI assessment**.

| Source | Safe broad filters | Avoid early |
|--------|-------------------|-------------|
| WB procnotices | `qterm`, notice type (EOI), country | Narrow sector only |
| UNDP | country/office RSS feed | Heavy keyword in connector |
| ReliefWeb | `job_type=Consultancy`, career category ICT/Programme | Remote-only hard filter |
| TED | CPV + keyword expert query | Over-restrictive CPV |
| UN Careers | job network/family codes | Single keyword only |

---

## 6. Identifiers and cross-source duplication

- **Canonical identity today:** per `source_id` + `source_reference` only.  
- **Likely duplicates:** DevelopmentAid ↔ UN agency originals ↔ ReliefWeb ↔ DevNetJobs mirrors.  
- **Do not** title-dedupe across sources in Phase 17B.  
- **Future signals:** original URL, donor project id (WB `project_id`), notice numbers, organisation name + deadline.

---

## 7. Detail-fetch patterns

| Pattern | Sources | Recommendation |
|---------|---------|----------------|
| List sufficient | WB procnotices (`notice_text`) | Single request per notice in API page |
| List + optional detail | DevelopmentAid | `fetch_details: true` default conservative limit |
| List + required detail | Workday (WFP) | `fetch_details` mandatory for Phase 8 |
| Feed item is complete | ReliefWeb job `body` | Single API call per job |
| HTML detail only | UNOPS, AfDB table | FETCH detail page per row |

**Example:** limit=25, detail fetch → ≤26 HTTP calls per source per run (DevelopmentAid model).

---

## 8. Rate limits and conservative limits

| Source | Guidance |
|--------|----------|
| WB procnotices | `rows=50`, offset pagination; cache; 1–2 req/s max |
| ReliefWeb | Respect appname quota; `limit` ≤ 50 per call |
| TED | Anonymous throttling; register API key if scheduled |
| UNDP RSS | Single feed poll per run |
| Initial JobHunter | **limit 25** (match FAO/DevelopmentAid) for new connectors |

No stress testing performed in Phase 17A.

---

## 9. Terms / robots / stability (non-legal)

Observations only — not legal advice.

| Source | Notes | Risk |
|--------|-------|------|
| WB procnotices | Open API documented for reuse | LOW |
| TED | Official reuse documentation | LOW |
| ReliefWeb | Official API ToS; appname tracking | LOW |
| UNDP RSS/JSON toolkit | Public documentation | LOW–MEDIUM |
| DevelopmentAid | Undocumented frontend API | MEDIUM |
| UN Careers joV2 JSON | Undocumented | MEDIUM–HIGH |
| DevNetJobs | Commercial site; scraping discouraged | HIGH |
| Workday endpoints | Undocumented | MEDIUM–HIGH |

---

## 10. Shared platforms

| Platform | Examples | Connector strategy |
|----------|----------|-------------------|
| Oracle Taleo REST | FAO | Per-portal config (already done) |
| Workday CXS API | WFP, possibly others | **Shared `WorkdayJobsClient`** parameterized by tenant/site |
| SAP Fieldglass | AfDB | Defer — account-centric |
| eRecruit / Impactpool-hosted | IFAD, some UN rosters | Prefer authoritative agency feed |
| **ReliefWeb** | Many UN/NGO jobs | **One meta-connector** vs many HTML scrapers |
| dgMarket | MCC, some MDB notices | Session friction — defer |

Do **not** merge UNOPS and UNDP merely because both are “UN”.

---

## 11. Phase 8 source-data sufficiency (Group A candidates)

| Connector candidate | Expected sufficiency |
|---------------------|---------------------|
| WB procnotices | ADEQUATE–PARTIAL (`notice_text`) |
| UNDP RSS/JSON | PARTIAL–GOOD_STRUCTURED |
| ReliefWeb jobs | ADEQUATE (full `body` when present) |
| AfDB consultant RSS/HTML | GOOD_STRUCTURED–ADEQUATE |

---

## 12. Implementation groups (for user review)

### Group A — strong Phase 17B candidates

- **World Bank procurement notices API** — documented, stable, good text, aligns with consultancy/EOI on bank projects.  
- **UNDP jobs RSS/JSON feeds** — official, no auth, strong development-sector coverage.  
- **ReliefWeb Jobs API** — after `appname` approval; covers WFP and many UN/NGO consultancies with full descriptions (high leverage).  
- **AfDB consultants RSS** — official feed, clear IC/firm EOI rows, land-relevant bank work.

*Reasoning:* PUBLIC_NO_AUTH or approved API key; stable IDs; fits existing `RawOpportunity` + scan adapter pattern; acceptable request amplification at limit 25.

### Group B — useful second batch

- **UNOPS careers marketplace** — HTML/structured detail; high ICA relevance; medium scrape cost.  
- **UN Careers (Inspira)** — if list API discovered or RSS; good detail JSON per id; needs heavy category filtering.  
- **TED Search API** — excellent API but volume and firm-procurement noise; needs CPV/keyword discipline.  
- **IFAD project procurement notices** — HTML list; medium land-sector fit.  
- **WFP direct Workday** — if not using ReliefWeb for WFP; shared Workday client.

### Group C — defer / monitor

- **ADB CSRN/CMS** — browse public, automation needs account or fragile HTML.  
- **GIZ** — fragmented portals.  
- **MCC / dgMarket** — session cookie barrier.  
- **World Bank RFx Now** — vendor auth for operational IC (keep monitoring; not worker-friendly).  
- **DevNetJobs** — no sanctioned API.

### Group D — not recommended currently

- **DevNetJobs scraping** — stability and ToS uncertainty.  
- **MCC dgMarket unattended scraping** — session/auth friction.  
- **Impactpool as primary** — aggregator, not authoritative source.

---

## 13. Expected connector shape (Group A)

Illustrative — mirror FAO/DevelopmentAid:

```
connectors/worldbank/
  client.py          # GET procnotices pagination
  mapper.py          # → RawOpportunity (source_reference = notice id)
  connector.py       # fetch + map
  normalizer.py
  identity.py

application/worldbank_scan/service.py   # or generic *ScanService
application/automation/source_adapters.py  # WorldBankSourceScanAdapter
```

**Generic scan service (Phase 17B design note, no refactor in 17A):**

Today each source duplicates orchestration (SourceScan, process, eligibility). A shared `ConfiguredSourceScanService` could accept:

- `connector_factory`
- `normalizer`
- `source_id` constants

**Risks:** premature abstraction before 3+ connectors; per-source assessment flags (`fetch_details`, notice types). **Recommendation:** implement 17B first connector with copy-paste from `DevelopmentAidScanService`; extract generic helper after second connector if duplication is clear.

---

## 14. automation.json implications (Phase 17B)

Current schema:

```json
{ "key": "…", "enabled": true, "keyword": "", "limit": 25, "fetch_details": true }
```

Likely extensions (validate in `parse_source_config`):

| Key | Example use |
|-----|-------------|
| `fetch_details` | DevelopmentAid, Workday, UNOPS HTML |
| `notice_types` | WB: `Request for Expression of Interest` |
| `feed_url` | UNDP: country/programme RSS |
| `countries` | Optional ISO filter (post-acquisition or API param) |

**Do not** move config to PostgreSQL (Phase 15/16 decision stands).  
Unknown keys should remain rejected until schema extended per connector.

---

## 15. Phase 17B test strategy (design only)

Per connector:

1. Fixture: search/list JSON (and detail JSON if applicable)  
2. Client pagination unit tests  
3. Mapper: required fields, `source_reference`, URLs, deadlines  
4. Malformed record isolation  
5. Integration: `RawOpportunity` → `OpportunityProcessingService` with test DB  
6. Repeat scan idempotency (same `source_reference`)  
7. Optional `@pytest.mark.live` smoke (excluded from CI)  
8. No network in default `pytest -q`

---

## 16. Unresolved questions (user decisions)

1. **ReliefWeb appname** — proceed with official request for JobHunter personal deployment?  
2. **World Bank scope** — project `procnotices` only for 17B, or also pursue RFx Now with credentials (not recommended unattended)?  
3. **UN Careers** — worth undocumented API investigation in 17B vs rely on ReliefWeb for Secretariat posts?  
4. **TED** — include despite firm-procurement noise and EU focus?  
5. **Generic scan service** — extract after connector #1 or #2?  
6. **17B batch size** — one connector per PR vs two (WB + UNDP)?

---

## 17. Phase 17B implementation (complete 2026-09-29)

**Approved and implemented:**

| Key | Job source id | Interface | Stable ID | Detail behaviour |
|-----|---------------|-----------|-----------|------------------|
| `worldbank` | `worldbank-procurement` | `search.worldbank.org/api/v2/procnotices` JSON | API `id` | `notice_text` in list payload |
| `undp` | `undp-jobs` | `jobs.undp.org/rss_feeds/rss.xml` (official RSS 0.91) | Oracle requisition id in link | RSS snippet only (no detail fetch) |
| `afdb` | `afdb-consultants` | AfDB consultants RSS | `node/{id}` from `guid` | Optional detail page for closing date + body |

**Deferred:** ReliefWeb (appname), UN Careers, UNOPS, TED, etc. → Phase 17C.

**17B vs 17A deltas observed (2026-09-29):**

- World Bank `procnotices` response is a **JSON array** under `procnotices` (not a nested `procnotice` object in current API).
- UNDP canonical discovery feed is `rss_feeds/rss.xml` (the `cj_rss_feed.cfm` page is an HTML index of feeds).
- AfDB RSS returns **HTTP 403** without a browser-style `User-Agent`; detail pages expose closing dates in HTML fields.

**Scan services:** per-source services retained (no generic refactor in 17B).

**Production validation (2026-09-29):** FAO, DevelopmentAid (429 fix), World Bank, UNDP
succeeded at configured limits; AfDB **disabled on NAS** after Cloudflare 403 on
official consultants RSS from worker network (see §19.3).

---

## 19. Phase 17C-1 — Authenticated DevelopmentAid & Devex (investigation only)

**Date:** 2026-09-29  
**Status:** Investigation complete — **no authenticated connector implementation**.

### 19.1 DevelopmentAid — current anonymous connector (VERIFIED in repo + live probe)

| Item | Value |
|------|--------|
| Search | `POST https://www.developmentaid.org/api/frontend/job/search` |
| Detail | `GET https://www.developmentaid.org/api/frontend/job/{id}` |
| Auth | **None** (no cookies, bearer, or API key) |
| Headers | `User-Agent`, `Content-Type: application/json`, `Accept: application/json` on POST; GET detail: `User-Agent`, `Accept` |
| Timeout | 60s |
| Pagination | `pageNumber`, `pageSize` (≤25 per page), stops at `limit` or `total` |
| `source_reference` | Numeric job `id` (string) |
| List fields used | `id`, `title`, `slug`, `organization`, `locationNames`, `deadline`, `postedDate`, `jobType`, `experience`, `fullyVisible`, `publicationStatus`, … |
| Detail fields used | `description` (HTML→text), `employer`, `sectors`, `languages`, `locations`, `expectedStartingDate`, `minimumExperience` |
| Detail fields **present in API but not mapped** (VERIFIED live keys) | `documents`, `emails`, `salary`, `lastUpdated`, `application`, `page_*` meta |
| Rate limit | Detail GET: `X-RateLimit-Limit: 20` (observed 2026-09-29); **429** `Too Many Attempts` |
| Throttle | **3.0s** between sequential detail GETs (`DevelopmentAidHttpPolicy`) |
| 429 retry | Up to **3** retries; `Retry-After` if present else exponential **2/4/8s** (cap 60s) |
| Circuit | After **2** consecutive detail failures after retries, stop remaining detail fetches; list rows retained |
| Phase 8 sufficiency | Generic length/heuristic (not DA-specific); with `fetch_details=true` and full HTML description typically **ADEQUATE**; list-only → **PARTIAL** / short text |

This is **not** DevelopmentAid’s official **partner external API** (see §19.2).

### 19.2 DevelopmentAid — authentication & official APIs

| Finding | Status |
|---------|--------|
| Web login UI | SPA at `/login` (INFERRED: browser session after credential POST; not inspected with user account) |
| Same `/api/frontend/...` when logged in | **UNKNOWN / REQUIRES AUTHENTICATED TEST** (likely same routes with session cookie — common SPA pattern) |
| **Official partner “external API”** | **VERIFIED** (public Zendesk/marketing): API key auth; CRUD on jobs/tenders/grants for **partner organisations**; paid/partnership onboarding (`partnership@developmentaid.org`); docs linked from [How To Use the Developmentaid API?](https://developmentaid.zendesk.com/hc/en-gb/articles/8946444465426-How-To-Use-the-Developmentaid-API) — oriented to **publish + partner retrieval**, not the anonymous frontend paths |
| Individual paid member login vs partner API | **UNKNOWN** whether personal subscription grants partner API keys or only UI features |
| Repository prior API-key work | **None found** in codebase/docs (only `api/frontend` connector) |

**Suitability classes**

- **A** Anonymous `/api/frontend/*` — **technically accessible**; production-validated with throttling.
- **B** Partner external API with API key — **accessible after contract**; **supported for automation** for partners; scope must be confirmed (read jobs/tenders vs post-only).
- **C** Browser session for member UI — **INFERRED** legitimate for human use; **automation suitability UNKNOWN** until ToS + DevTools review.
- **D** Scraping HTML / bypassing limits — **not recommended**.

### 19.3 AfDB reminder (17B production)

Official consultants RSS blocked by **Cloudflare** from Synology egress; connector remains in registry; **disable `afdb` in production** until a non-CF official interface is confirmed from the **worker network**.

### 19.4 Devex — investigation summary

| Item | Finding | Status |
|------|---------|--------|
| Job search URL | `https://www.devex.com/jobs/search` (and related Career Hub) | **403** from probe IP (likely bot/WAF — same class as AfDB on NAS) |
| Public robots.txt | Not retrieved (403 on probe) | **UNKNOWN** |
| Official **job search/read API** for subscribers | **Not found** in Devex support docs | **VERIFIED** for absence of *search* API |
| Official **job posting API** | `POST` XML to `https://www.devex.com/api/public_secure/job_uploads/job_upload.xml` with org key/password — **employers post jobs**, not discover them | [Job posting API information](https://support.devex.com/hc/en-us/articles/360000127713-Job-posting-API-information) |
| Third-party APIs (Parse, Apify, Spider) | Scraping/wrapper services | **Not official** — treat as **D** |
| Logged-in SPA JSON endpoints | Not observed without user session | **REQUIRES AUTHENTICATED TEST** |
| Pipeline fit | Same `RawOpportunity` + scan service pattern **if** a stable JSON/feed and lawful access exist | **Blocked pending access model** |

**Devex value (INFERRED):** High overlap with DevelopmentAid, ReliefWeb, and agency boards for development jobs/consultancies; **unique** postings likely exist but volume/overlap unquantified without authenticated sampling.

### 19.5 Anonymous vs authenticated DevelopmentAid (comparison)

**Empirical check (2026-09-29, one public `fullyVisible` job):** logged-in and
anonymous/incognito detail JSON returned the same useful fields (title, dates,
locations, languages, sectors, `minimumExperience`, full HTML `description`,
`url`, organisation metadata). `documents=[]`, `emails=null`, `hasEmails=true`
with application instructions inside `description`. **No demonstrated benefit**
from automating username/password login for ordinary public listings.
Revisit auth only for subscriber-only listings or when `documents[]` / ToR
attachments require a session.

| Capability | Anonymous (current) | Authenticated (member/partner) | Value to JobHunter |
|------------|--------------------|--------------------------------|--------------------|
| Discovery coverage | Broad public search JSON | Not tested beyond one job | Medium–high if materially more |
| Title / deadline / location | VERIFIED list+detail | **Same on tested job** | Baseline met anonymously |
| Description / ToR | HTML `description`; `documents[]` often empty | **Same on tested job** | High if docs unlock elsewhere |
| Organisation | List `organization` + detail `employer` | **Same on tested job** | Medium |
| Consultant vs firm | `jobType` / `type.name` | **Same on tested job** | Medium |
| Sectors / languages | Detail when fetched | **Same on tested job** | Medium |
| Stable ID | `id` | **INFERRED** same | High |
| Rate limits | 20/detail window + 429 | Not re-tested | Operational |
| Assessment sufficiency | ADEQUATE with details (typical) | **Same on tested job** | High |

### 19.6 Implementation options (not approved — do not implement)

**DevelopmentAid:** DA-A anonymous only (current); DA-B anonymous list + auth detail enrichment; DA-C full auth discovery+detail; DA-D **partner official API** if read access is contractually available.

**Devex:** DX-A public only (currently **blocked** on many egress IPs); DX-B public+auth detail; DX-C auth discovery+detail; DX-D official feed (only **job upload** API documented — wrong direction for acquisition).

### 19.7 Proposed secrets architecture (design only)

- Store **only** in `.env` / Synology secrets: e.g. `JOBHUNTER_DEVELOPMENTAID_API_KEY` (partner API) or session-related secrets **if** a supported mechanism is chosen — **not** username/password in DB/Git/logs.
- Prefer **API key header** for partner API over scraping session cookies.
- Session cookies: short-lived, in-memory per scan only; never in `SourceScan.error_summary`, emails, or Streamlit.
- Tests: fixtures + mocked HTTP; live auth tests behind optional marker and env.

### 19.8 Phase 17C roadmap (after 17C-1)

1. **ReliefWeb** (appname) — still highest-leverage meta-source.  
2. **DevelopmentAid** — user DevTools session compare anonymous vs logged-in; then decide DA-B vs DA-D.  
3. **Devex** — only after DevTools proves stable JSON + terms allow unattended use.  
4. **AfDB** — re-test RSS from NAS container; no Cloudflare bypass.  
5. UNOPS, TED, etc. — unchanged from §17.

### 19.9 Manual test checklist (for Jan)

See Phase 17C-1 final report (chat); safe to share: endpoint URLs, methods, status codes, JSON **field names**, rate-limit **header names**, redacted schemas — **not** passwords, cookies, Authorization, or full HAR dumps with secrets.

## 20. Phase 17C-2 — DevelopmentAid metadata utilisation (complete)

**Status:** Complete (2026-09-29). Anonymous connector unchanged; no auth, no migration.

### 20.1 Design

- **Canonical `Opportunity` columns:** unchanged (title, organisation, location,
  description, dates, `opportunity_type`, `source_status`).
- **Source-neutral `structured_facts` in `raw_opportunities.extra`:** sectors,
  languages, minimum experience, organisation type, contract label,
  application URL, content last updated, salary summary, document metadata
  (URLs only — no download).
- **Assessment:** extra `OpportunityEvidenceField` prompt slots + digest includes
  `structured_facts` from latest raw observation (re-assessment when metadata
  changes on rescan).
- **Provenance URLs:** `opportunity_sources.source_url` = DevelopmentAid listing;
  `original_url` = external application URL when `detail.url` differs.
- **Sentinel dates:** `9999-12-28` (and year ≥9999) → not stored as
  `expected_start_date`.
- **Emails / `hasEmails`:** not persisted; semantics unproven — application
  contact often in `description`.
- **Documents:** metadata mapped when present; attachment download deferred.

### 20.2 Historical rescans

New scan → new `raw_opportunities` row → same canonical identity → opportunity
fields updated when material; structured facts refreshed on latest observation;
content digest changes when canonical fields or `structured_facts` change →
assessment reuse invalidated when appropriate. No bulk re-assessment job added.

---

## 21. Phase 17D — ReliefWeb, TED, and candidate review (2026-09-29)

### 21.1 Candidate classification (A/B/C/D)

| Source | Class | Rationale |
|--------|-------|-----------|
| **ReliefWeb Jobs** | **A** (implemented) | Official documented API v2; single call returns full `body`; requires pre-approved `appname` in `.env` (`JOBHUNTER_RELIEFWEB_APPNAME`). |
| **TED EU** | **A** (implemented) | Official Search API v3; anonymous POST; expert query + keyword from automation. |
| **UNDP / WB / FAO / DA** | — | Already in production (17B/17C). |
| **AfDB** | **C/D** | RSS implemented; production **disabled** on NAS (Cloudflare 403). |
| **UNOPS** | **B** | PUBLIC HTML marketplace; no stable public API (**INFERRED**); defer HTML connector. |
| **UN Careers / Inspira** | **C** | Detail JSON works when `jobId` known (**VERIFIED** probe); list API undocumented (**UNKNOWN**); mostly staff posts. |
| **ADB CSRN/CMS** | **C** | Strategically important; public browse at `csrn.adb.org` but no read API (**VERIFIED** docs); HTML/SPA + CMS account for proposals — defer dedicated connector. |
| **IFAD** | **C/D** | Staff `job.ifad.org` DNS/blocked from some egress (**UNKNOWN**); procurement HTML on `ifad.org` returned 403 from probe — defer. |
| **WFP direct** | **B/C** | Workday CXS POST undocumented (**INFERRED**); ReliefWeb covers many WFP consultancies — defer direct Workday. |
| **GIZ** | **D** | Fragmented portals (`jobs.giz.de`, country OKV sites); no single feed (**INFERRED**). |
| **Devex** | **D/C** | No job **read** API (**VERIFIED**); public site often 403 from datacenter IPs; employer upload API only. Manual DevTools if revisiting. |

### 21.2 Implemented connectors (17D)

| Key | `source_id` | Interface | `source_reference` | Detail | Sufficiency |
|-----|-------------|-----------|-------------------|--------|-------------|
| `reliefweb` | `reliefweb-jobs` | `POST api.reliefweb.int/v2/jobs?appname=…` | ReliefWeb job `id` | In list (`body` HTML) | **ADEQUATE** when body present |
| `ted` | `ted-eu-procurement` | `POST api.ted.europa.eu/v3/notices/search` | `publication-number` | In search response | **ADEQUATE** / **PARTIAL** (firm procurement noise) |

### 21.3 Devex — conclusion

No unattended connector. Documented APIs are employer **job upload** only. Public automated access unreliable; logged-in read endpoints **UNKNOWN** — use Chrome DevTools (Network → XHR/Fetch) comparing logged-in vs incognito on job search/detail; share field names and URL patterns only.

### 21.4 ADB — conclusion

Prioritise a future **HTML/CSRN browse connector** (class B) after a NAS egress probe of `csrn.adb.org` and sample listing/detail HTML stability. Do not automate CMS login or proposal submission.

### 21.5 Operations

- ReliefWeb: 1000 API calls/day quota (official); start `limit: 10`; one POST per scan page.
- TED: one POST per scan; default LAND-CORE expert query when `keyword` empty; start `limit: 10`.
- ReliefWeb **disabled** in `automation.example.json` until `JOBHUNTER_RELIEFWEB_APPNAME` is set.

### 21.6 TED default query correction (production validation, 2026-09-29)

Synology TED-only validation (`TedScanService.run_scan(limit=5, apply=True)`) reported
`SUCCESS` with **`retrieved=0`** while Phase 17D live probes against the same API returned
notices for single-term queries (e.g. `FT~"GIS"`).

**Root cause:** TED Search API v3 does not treat OR inside a single `FT~( … )` group as
disjunctive full-text search. The shipped default:

`FT~("land administration" OR cadastre OR …) AND PD>=…`

returned `notices: []` and `totalNoticeCount: 0`. Valid syntax joins **separate**
predicates: `(FT~"land administration" OR FT~cadastre OR …) AND PD>=…`.

**Fix (syntax):** separate `FT~` predicates joined by OR. An interim ten-term default
(§21.7) was later **replaced by LAND-CORE** in Phase 17D-3. Non-empty `keyword` in
automation JSON still maps to a single `FT~"keyword"` clause.

**After NAS re-validation**, enable TED with empty keyword and a small limit:

```json
{
  "key": "ted",
  "enabled": true,
  "keyword": "",
  "limit": 10
}
```

Keep `enabled: false` in the repository example until production validation succeeds.

### 21.7 TED acquisition relevance tuning (17D-2 investigation, 2026-09-29)

Post-syntax-fix live validation returned **~2765** ACTIVE notices for the ten-term default, but
recent-result samples were dominated by **GIS/SDI substring noise** (e.g. Croatian
*administrativnom* matching `FT~GIS`; French **SDIS** fire services matching `FT~SDI`) and
broad IT/environmental hits.

**Term-level signal (ACTIVE, `PD>=20240101`, investigation counts):** high-value land/cadastre
terms (`cadastre` ~400, `cadastral` ~471, `cadastral survey` ~281) vs noisy abbreviations
(`GIS` ~1297, `SDI` ~752) and overly broad phrases (`surveying` ~8423, `mapping` ~1752).
Zero-hit phrases in TED full text: `land information system`, `land registry`, `spatial data
infrastructure`.

**LAND-CORE default (implemented 17D-3):** eight OR predicates — land administration,
cadastre, cadastral, property registration, land registration, land registry, land
information system, cadastral survey — (~572 ACTIVE notices in investigation). Removed
from default: GIS, SDI, geospatial, geographic information, spatial data, digital
transformation (substring/acronym noise and low precision). Use explicit `keyword` for
those concepts when needed.

**TED role:** secondary source — EU cadastre/LIS programmes and firm/service procurement;
weak for direct individual-consultant posts vs FAO, DevelopmentAid, World Bank, UNDP.
Initial scheduled `limit: 10` when enabled.

**CPV (deferred):** cadastre samples often use **71354300** (cadastral services) and
**71355000** (surveying). No CPV filter in the connector; possible future ranking/context
or optional OR expansion only.

Keep `enabled: false` in `automation.example.json` until NAS validation of LAND-CORE.

---

## 22. Phase 17E — ADB CSRN, UNOPS, UN Careers (investigation, 2026-09-29)

Production portfolio at investigation time: **FAO, DevelopmentAid, World Bank, UNDP, TED**
(validated); **ReliefWeb** implemented pending appname; **AfDB** disabled (Cloudflare 403
from NAS/datacenter egress).

### 22.1 Connector extension contract (unchanged)

New sources follow the existing pattern: `connectors/<source>/` (`identity`, `client` or
`connector`, `mapper`, `normalizer`), `application/<source>_scan/service.py`,
`SourceScanAdapter` in `source_adapters.py`, `KNOWN_SOURCE_KEYS` + `automation.json` entry,
`source_id` + `source_reference` idempotency, `RawOpportunity` with provenance and optional
`structured_facts` in `extra`, Phase 8 sufficiency via list vs detail text. No schema
migration required for new connectors.

### 22.2 ADB — CSRN / CMS

| Item | Finding |
|------|---------|
| **Public entry** | `https://csrn.adb.org` → `https://selfservice.adb.org/OA_HTML/OA.jsp?OAFunc=XXCRS_CSRN_HOME_PAGE` (Oracle E-Business **CMS Consulting Opportunities**). |
| **CSRN vs CMS** | **CSRN** = Consulting Services Recruitment Notice (public notice of consulting need). **CMS** = Consultant Management System (same portal family; registration/proposal workflows are **account-gated**). |
| **Method / type** | **GET** server-rendered **HTML** (Oracle UIX/ADF); not JSON/RSS. |
| **Auth** | **Browse/search listing without login** (verified 2026-09-29). Proposal submission and consultant registration require CMS account — **out of scope**. |
| **Pagination** | **25 per page**, “Next 25”, keyword search, filters (Consultant Type individual/firm, country, sector, etc.). |
| **Stable ID** | Notice id in title, e.g. **`E-059508-001`**; project links to `adb.org/projects/…` (main site may **403** from some IPs; `selfservice.adb.org` listing worked). |
| **IC vs firm** | Titles distinguish **National … Specialist** (individual) vs **Firm** / QCBS packages; Consultant Type filter on UI. |
| **Detail / ToR** | Notice detail via CSRN/OA navigation (HTML); depth **PARTIAL–ADEQUATE** expected from notice + linked project docs — **verify per notice** in implementation. |
| **WAF** | `www.adb.org` returned **403** from investigation egress; **`selfservice.adb.org` CSRN home returned 200** (~127 KB HTML). **NAS egress probe required** before scheduling. |
| **Classification** | **B** — stable public HTML suitable for a **conservative** connector (no login, no CMS automation). |

**Relevance samples (investigation labels):**

| Sample | Class |
|--------|-------|
| IWRM voluntary **land donation** monitoring (E-055197-001) | **HIGH** |
| Greater Peshawar **urban transport** master plan consultancy | **MEDIUM** |
| **National Financial Specialist** (fisheries project) | **MEDIUM** (IC) |
| Engineering design consultants (multi-sector CS-01) | **LOW–MEDIUM** (firm) |

Approx. mix on one listing page: **both** firm QCBS-style packages and **individual specialist** posts; land/GIS hits are sparse in titles but strategically aligned when present.

**Production validation (2026-09-29):** NAS scan `SUCCESS`, `retrieved 10`, `processed 10`,
`failed 0` with `fetch_details: false`. Safe to enable `adb` in production `automation.json`
(`limit: 10`).

**Implemented (17E-1 / 17E-1A, 2026-09-29):** automation key **`adb`** → `source_id` **`adb-csrn`**.
`AdbCsrnConnector` — GET listing + cookie-backed pagination; parse Oracle table rows;
`source_reference=E-…`; `source_url` listing anchor; `application_url` → `csrn.adb.org`.
**`fetch_details` not implemented** — anonymous POST to `view_csrn` returns Oracle error
page; list fields yield Phase 8 **PARTIAL** sufficiency (not ADEQUATE).

**Duplicate listing rows:** one CSRN notice id (`E-…`) is one opportunity; multiple table
rows are expertise variants merged into `structured_facts.expertise` (sorted, deduplicated)
before persistence. Without aggregation, identical `raw_opportunity` ids caused later rows
to be skipped by observation idempotency (first row only).

**NAS egress (2026-09-29):** `https://selfservice.adb.org/OA_HTML/OA.jsp?OAFunc=XXCRS_CSRN_HOME_PAGE`
→ **HTTP/1.1 200 OK** from Synology NAS (production prerequisite satisfied).

### 22.3 UNOPS — Careers Marketplace (Avature)

| Item | Finding |
|------|---------|
| **Entry** | `https://jobs.unops.org` → **`https://careers.unops.org`** (Avature **Careers Marketplace**). |
| **Type** | **SPA** + Avature wizard metadata (`InstantSearchDatasource`, encrypted `listSpecId` / `searchIndexId` in page HTML). |
| **Auth** | **Search and view postings without login**; apply requires account. |
| **List** | Home page exposes open positions (title, duty station, seniority, deadline); `/careersmarketplace/SearchJobs` returns **200 HTML**. |
| **Stable ID** | Avature internal job id in URLs (implementation must extract from listing/detail links — **not** documented public API). |
| **ICA / consultancy** | Titles include **Specialist**, **Retainer**, **home based**; also many **administration** and **internal** posts — requires filtering. |
| **Sample** | **Cartographer Specialist** (Tirana/home-based) — **HIGH** for geo; most carousel items — **LOW** for domain. |
| **WAF / SSL** | Public HTTPS works via **curl**; Python `urllib` on Windows hit **SSL verify** issues (environment-specific). No Cloudflare block observed. |
| **Classification** | **C** — useful portal but **undocumented Avature XHR**; fragile without official API. |

**Proposed architecture if pursued later:** reverse-engineer Avature search POST from
documented browser network capture **or** parse stable SSR fragments only — high
maintenance. **Defer** until ReliefWeb overlap assessed.

### 22.4 UN Careers / Inspira

**NAS egress (2026-09-29):** `GET https://careers.un.org/jobfeed?language=en` from Synology
→ **HTTP/1.1 403 Forbidden** (`Server: CloudFront`, `X-Cache: Error from cloudfront`).
**17E-2 UN Careers RSS is deferred** until an official feed or API works from production
egress (do not implement RSS connector based on dev-only 200 responses).

| Item | Finding |
|------|---------|
| **Official list feed** | **`GET https://careers.un.org/jobfeed?language=en`** — **RSS 2.0**, ~**481** items (2026-09-29), generator documented in feed. |
| **Stable ID** | **`Job ID`** in RSS description + URL `…/jobSearchDescription/{id}?language=en`. |
| **Detail** | Job pages are **Angular SPA** shell; `/api/job/{id}` paths return SPA HTML, **not** JSON in anonymous GET probes. Prior “detail JSON when jobId known” **not confirmed** as a stable public API in this probe. |
| **Consultancy signal** | RSS `Level : **CON**` (e.g. GIS Developer, Urban Planning Consultant, Senior Digital Transformation Consultant); majority are **P/G/NO** staff posts. |
| **Keyword hits in feed** | GIS **26** (many false positives e.g. “log**is**tics”); geospatial **0**; land **1**; cadast **0**; information system **6**; digital transformation **1**; urban planning **1**. |
| **Classification** | **A** for **RSS acquisition**; **B/C** for full description (SPA / possible Workday backend, no confirmed CXS JSON). |

**Proposed architecture (not implemented):** `un-careers` connector via **official RSS**
(same pattern as UNDP/AfDB RSS): one GET per scan; `source_reference=job id`; optional
detail fetch of HTML or future discovered JSON — `fetch_details` default **false** initially.

### 22.5 Comparison matrix

| | **ADB CSRN** | **UNOPS Avature** | **UN Careers RSS** |
|--|--------------|-------------------|---------------------|
| Relevance (land/Geo-ICT) | **High** (when notices exist) | Medium | Low–medium |
| IC relevance | Both IC & firm | ICA/LICA mixed with ops staff | Mostly staff; some **CON** |
| Interface | HTML (Oracle) | Avature SPA | **RSS** + SPA detail |
| Auth (read) | No | No | No |
| Stable ID | **E-…-…** | Avature id | **Job ID** |
| Description quality | PARTIAL–ADEQUATE | PARTIAL (list); detail TBD | **PARTIAL** in RSS |
| WAF risk | Low on selfservice; adb.org 403 | Low observed | Low |
| Complexity | Medium HTML | High | **Low** (RSS) |
| Overlap with DA/ReliefWeb | Moderate | **High** (ReliefWeb lists UNOPS) | Moderate |
| Class | **B** | **C** | **A** (feed) |

### 22.6 Recommended implementation order

1. **17E-1 — ADB CSRN (class B)** — **done** (list-only; NAS 200 validated).
2. **17E-2 — UN Careers** — **deferred** (NAS RSS 403); investigate alternative official
   read interface from production egress before implementation.
3. **Defer UNOPS (class C)** — implement only if ReliefWeb (once enabled) does not cover
   enough UNOPS ICA/geo roles with adequate descriptions.

**Do not implement:** AfDB until Cloudflare egress fixed; Devex; UNOPS Avature scraping
without official read API.

### 22.7 ReliefWeb interaction

ReliefWeb aggregates many **UN agency** vacancies (including UNOPS). Direct **UNOPS**
connector adds marginal value if ReliefWeb is enabled with approved appname. **UN
Careers RSS** still adds **Secretariat-specific** posts not always mirrored elsewhere.
**ADB CSRN** has **low overlap** with current sources — highest incremental value.

### 22.8 Portfolio blind spots (future only)

IFAD, WFP (direct Workday), GIZ, MCC, regional banks, **IOM**, **UN-Habitat** specialist
rosters — not investigated in 17E. TED covers EU firm procurement, not IC recruitment.

---

## 18. References (public)

- World Bank procnotices: `https://search.worldbank.org/api/v2/procnotices`  
- WB RFx Now FAQ: `https://thedocs.worldbank.org/.../Operational-Consulting-FAQ.pdf`  
- UNDP RSS: `https://jobs.undp.org/cj_rss_feed.cfm`  
- UNDP JSON feeds: `https://public-components.undp.org/help/howto/jobs.cfm`  
- ReliefWeb API: `https://apidoc.reliefweb.int/`  
- TED Search API: `https://docs.ted.europa.eu/api/latest/search.html`  
- AfDB consultants RSS: `https://www.afdb.org/en/about-us/careers/current-vacancies/consultants/rss/`  
- ADB CSRN: `https://csrn.adb.org` (→ `https://selfservice.adb.org/OA_HTML/OA.jsp?OAFunc=XXCRS_CSRN_HOME_PAGE`)  
- UN Careers RSS: `https://careers.un.org/jobfeed?language=en`  
- UNOPS Careers: `https://careers.unops.org/`  
- DevelopmentAid search API (baseline): `https://www.developmentaid.org/api/frontend/job/search`
- DevelopmentAid partner API (Zendesk intro): `https://developmentaid.zendesk.com/hc/en-gb/articles/8946444465426-How-To-Use-the-Developmentaid-API`
- Devex job posting API (employers only): `https://support.devex.com/hc/en-us/articles/360000127713-Job-posting-API-information`
