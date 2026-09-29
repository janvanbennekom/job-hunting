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

---

## 18. References (public)

- World Bank procnotices: `https://search.worldbank.org/api/v2/procnotices`  
- WB RFx Now FAQ: `https://thedocs.worldbank.org/.../Operational-Consulting-FAQ.pdf`  
- UNDP RSS: `https://jobs.undp.org/cj_rss_feed.cfm`  
- UNDP JSON feeds: `https://public-components.undp.org/help/howto/jobs.cfm`  
- ReliefWeb API: `https://apidoc.reliefweb.int/`  
- TED Search API: `https://docs.ted.europa.eu/api/latest/search.html`  
- AfDB consultants RSS: `https://www.afdb.org/en/about-us/careers/current-vacancies/consultants/rss/`  
- ADB CSRN: `https://csrn.adb.org`  
- DevelopmentAid search API (baseline): `https://www.developmentaid.org/api/frontend/job/search`
