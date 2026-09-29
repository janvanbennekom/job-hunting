# architecture.md

## 1. Purpose

This document defines the architecture of the Job Hunting AI Agent.

The system is a personal AI-assisted opportunity discovery, assessment,
ranking, tracking, and application-support platform.

It is designed specifically around the professional profile and evolving
job-search strategy of Jan van Bennekom-Minnema.

The system searches multiple external sources, collects potential
opportunities, normalizes and deduplicates them, applies eligibility rules,
assesses professional relevance and profile fit, ranks opportunities, and
presents the results for human review.

For selected opportunities, the system can subsequently support application
tracking and generation of tailored application documents.

The architecture must support an evolving search strategy. The user should be
able to discuss changing requirements with the system in natural language and,
after confirmation, persist those changes as structured search strategy.


## 2. Architectural Goals

The architecture should support the following goals:

1. Personalised opportunity discovery
2. High recall during initial discovery
3. Progressive filtering and ranking
4. Evidence-based profile matching
5. Explainable AI assessments
6. Persistent state across scans
7. Conversational management of search preferences
8. Multiple heterogeneous opportunity sources
9. Scheduled autonomous operation
10. Human control over important decisions
11. Traceability and provenance
12. Incremental development
13. Replaceable external integrations
14. Independent cloud deployment
15. Reasonable operating cost


## 3. Architectural Principles

The principles defined in AGENTS.md apply throughout the architecture.

Particularly important architectural principles are:

- separate deterministic processing from AI reasoning;
- separate source acquisition from opportunity processing;
- preserve source provenance;
- persist important state explicitly;
- treat professional evidence separately from search preferences;
- use structured AI outputs where application logic depends on AI results;
- keep AI model/provider integration replaceable;
- keep source connectors replaceable;
- maintain human control over persistent preference changes and applications;
- favour simple components over unnecessary distributed infrastructure.

The initial system should be implemented as a modular monolith.

Do not introduce microservices unless a demonstrated requirement later
justifies them.


## 4. System Context

The system interacts with four main external contexts:

### User

The user:

- maintains professional information;
- maintains or discusses search preferences;
- reviews opportunities;
- provides relevance feedback;
- selects opportunities to pursue;
- tracks applications;
- reviews generated documents.

### Opportunity Sources

External sources provide job, consultancy, procurement, roster, and related
professional opportunities.

Examples include:

- World Bank;
- ADB;
- UNOPS;
- FAO;
- UNDP;
- AfDB;
- IFAD;
- UN Careers;
- UN-Habitat;
- GIZ;
- EU/TED;
- MCC;
- international consulting firms;
- discovery/aggregator sites.

Different sources may require different acquisition mechanisms.

### AI Model Provider

AI models provide semantic reasoning and generation for tasks such as:

- opportunity interpretation;
- professional relevance assessment;
- profile matching;
- ranking explanation;
- conversational strategy management;
- CV tailoring;
- cover-letter generation.

### Notification Services

The system may send scheduled opportunity reports and other notifications,
initially by email.


## 5. High-Level Architecture

The logical architecture is:

    ┌────────────────────────────────────────────────────────────┐
    │                        User Interface                      │
    │                                                            │
    │ Dashboard │ Opportunity Review │ Chat │ Tracking │ Profile │
    └────────────────────────────┬───────────────────────────────┘
                                 │
                                 ▼
    ┌────────────────────────────────────────────────────────────┐
    │                    Application Layer                       │
    │                                                            │
    │ Search │ Review │ Strategy │ Tracking │ Personalisation    │
    └────────────────────────────┬───────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐
    │ Deterministic   │ │ AI / Reasoning  │ │ Source           │
    │ Domain Services │ │ Services        │ │ Connectors       │
    │                 │ │                 │ │                  │
    │ filtering       │ │ relevance       │ │ API              │
    │ deduplication   │ │ matching        │ │ HTTP             │
    │ lifecycle       │ │ explanation     │ │ browser          │
    │ ranking maths   │ │ conversation    │ │ discovery        │
    └────────┬────────┘ └────────┬────────┘ └────────┬─────────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
                                 ▼
    ┌────────────────────────────────────────────────────────────┐
    │                     Persistence Layer                      │
    │                                                            │
    │ PostgreSQL │ Documents │ Raw Source Data │ Audit/History   │
    └────────────────────────────────────────────────────────────┘


## 6. Opportunity Processing Pipeline

A scan should conceptually execute the following pipeline:

    Source
      │
      ▼
    Acquire
      │
      ▼
    Raw Opportunity
      │
      ▼
    Normalize
      │
      ▼
    Identify / Deduplicate
      │
      ▼
    Detect Changes
      │
      ▼
    Deterministic Eligibility Filter (Phase 7)
      │
      ▼
    AI Profile / Relevance Assessment (Phase 8)
      │
      ▼
    Ranking (Phase 9)
      │
      ▼
    Persist Assessment
      │
      ▼
    Dashboard / Notification

Each stage should have an explicit input and output.

A failure in an AI assessment should not cause acquisition or persistence of
the opportunity itself to fail.


## 7. Core Domain Areas

### 7.1 Sources

Responsible for:

- source configuration;
- source priority;
- acquisition method;
- authentication metadata;
- active/archive state;
- scan history;
- source health.

### 7.2 Search Criteria

Responsible for:

- search themes;
- primary search criteria;
- secondary search criteria;
- keyword groups;
- source-specific search variations;
- active/inactive criteria.

### 7.3 Opportunities

Responsible for:

- normalized opportunity representation;
- source relationships;
- raw source information;
- deduplication;
- change detection;
- lifecycle;
- eligibility;
- assessments;
- rankings.

#### Opportunity Scope

JobHunter targets professional opportunities that can be undertaken by the
user as a single consultant.

The contractual arrangement may be:

- directly with the user as an individual consultant; or
- through JVB GIS Consulting as the user's one-person consulting firm.

The system does not target general consulting-firm procurements requiring
multi-person teams, consortium arrangements, or organisational delivery
capacity beyond a single consultant.

A procurement or tender notice may still be a relevant source when the
underlying assignment is for a single consultant.

This distinction should be considered during opportunity normalization,
eligibility assessment, and filtering.


### 7.4 Professional Profile

Responsible for authoritative evidence describing what the user can credibly
claim.

The professional profile includes:

- professional positioning;
- professional services;
- assignments and project experience;
- capabilities and capability categories;
- assignment-to-capability evidence relationships;
- technical and professional skills;
- language capabilities;
- countries of professional experience (country experience evidence);
- authoritative profile documents.

Capabilities represent a controlled classification of professional experience,
including domain, system type, system development, data and analysis, quality
assurance, management and strategy, and capacity development.

Assignments may be associated with multiple capabilities. These associations
form structured evidence that can later be used for opportunity matching.

Capabilities are distinct from skills and technologies. For example,
"System integration and interoperability" is a capability, while PostgreSQL,
Python or GeoServer are skills/technologies used in delivering that capability.

The detailed CV, the Professional Services document, and the structured
project spreadsheet are authoritative source material for the professional
profile. Structured profile data may be derived or imported from these sources
while retaining source provenance.

### 7.5 Search Strategy

Responsible for what the user currently wants.

`SearchStrategy` is the stable logical identity. Configurable content lives on
immutable `SearchStrategyRevision` snapshots. `SearchStrategy.current_revision_id`
identifies the current active revision. Material changes create a new revision
rather than modifying an existing active revision in place.

Phase 4 stores strategy state only. Deterministic filtering remains Phase 7; AI
matching remains Phase 8; ranking remains Phase 9; conversational modification
remains Phase 11.

Search Strategy is distinct from Professional Profile. Do not copy professional
evidence into Search Strategy to make matching easier, and do not link strategy
themes to `ProfessionalService` rows. For example, PostgreSQL experience belongs
to the profile; wanting more implementation-oriented assignments belongs to
strategy.

Revision content uses four semantics:

A. **SearchTheme** — positive area of interest (for example LIS
   implementation). Carries ordinal `PreferenceStrength` where applicable.

B. **StrategyCriterion / PREFERENCE** — ranking preference; absence normally
   does not reject an opportunity.

C. **StrategyCriterion / HARD_CONSTRAINT** — input to deterministic eligibility
   filtering; a clear violation may make an opportunity unsuitable.

D. **ExclusionCriterion** — explicit opportunity category to exclude when
   clearly matched.

`StrategyCriterion` (not to be confused with future acquisition or discovery
search criteria) has category `PREFERENCE` or `HARD_CONSTRAINT`, a closed
`StrategyParameterCode` vocabulary, and a structured `value` validated per code.
Phase 4 uses at most one criterion per `(revision, category, code)` for the
MVP. JSON must not become an unrestricted key/value configuration bag.

Ordinal preference strength for themes and preference criteria:

    STRONGLY_PREFERRED
    PREFERRED
    ACCEPTABLE
    LESS_PREFERRED

Do not introduce numeric ranking weights in Phase 4. Later ranking may map
these levels to small configured contributions.

Examples of strategy concerns (not an exhaustive list):

- preferred service or work themes;
- assignment types and delivery mode;
- geography, duration, travel, and remote/on-site characteristics;
- hard limits and explicit exclusions.

Long continuous overseas assignments should initially be representable as a
preference (for example `LESS_PREFERRED`), not automatically as a hard
exclusion.

### 7.6 Strategy History

Changes to search strategy must be traceable through immutable revisions.

Each `SearchStrategyRevision` stores:

- `revision_number`;
- `status` (`ACTIVE` or `SUPERSEDED`; `DRAFT` deferred until Phase 11 if
  needed);
- `created_at`;
- `change_summary`;
- `change_source`;
- `supersedes_revision_id` (optional lineage);
- `content_hash` (canonical hash of revision content).

`effective_from` and `user_confirmed` are deferred until they have actual
application behaviour.

The same semantic seed content (matching `content_hash`) must not create a new
revision. Changed semantic content creates and activates a new revision.

Later eligibility assessments, relevance or profile-match assessments, and
rankings should be able to record the `SearchStrategyRevision` id used when the
opportunity was evaluated, so the system can answer what strategy was in effect
at assessment time.

### 7.7 User Feedback

Opportunity feedback is stored independently from AI assessments.

Examples:

- relevant;
- not relevant;
- strong match;
- too advisory;
- too managerial;
- too junior;
- too GIS-generic;
- too remote-sensing focused;
- similar opportunities wanted;
- do not show similar opportunities.

Feedback may later be used to propose changes to Search Strategy.

### 7.8 Applications

Responsible for:

- decision to pursue;
- application status;
- application date;
- response history;
- follow-up;
- remarks;
- generated documents;
- submitted documents.


## 8. Professional Context Model

The architecture separates professional context into two primary categories:

    ┌───────────────────────────┐
    │   Professional Evidence   │
    │                           │
    │ What can Jan credibly     │
    │ claim?                    │
    │                           │
    │ CV                        │
    │ Professional Services     │
    │ Assignments               │
    │ Skills                    │
    │ Languages                 │
    │ Experience                │
    └─────────────┬─────────────┘
                  │
                  │ evidence
                  ▼
             Profile Matching


    ┌───────────────────────────┐
    │ Current Search Strategy   │
    │                           │
    │ What does Jan currently   │
    │ want?                     │
    │                           │
    │ Priorities                │
    │ Preferences               │
    │ Constraints               │
    │ Search themes             │
    │ Ranking preferences       │
    └─────────────┬─────────────┘
                  │
                  │ preferences
                  ▼
              Discovery /
              Filtering /
              Ranking

Professional evidence must not be modified simply because search preferences
change.


## 9. Conversational Strategy Management

The system should eventually provide a conversational interface for managing
search strategy.

Example:

    User:
    "I am seeing too many generic GIS opportunities. Give more priority
    to LIS implementation, system integration and Geo-ICT architecture."

The conversational strategy component should:

1. retrieve the current search strategy;
2. interpret the user's requested change;
3. translate the request into structured proposed changes;
4. explain the proposed changes;
5. request confirmation for material persistent changes;
6. persist the confirmed strategy revision;
7. retain the previous strategy in history.

Conceptual flow:

    User
      │
      ▼
    Conversation
      │
      ▼
    Context / Strategy Agent
      │
      ▼
    Proposed Structured Changes
      │
      ▼
    User Confirmation
      │
      ▼
    Persist New Strategy Revision

Conversation history itself is not the authoritative store of search
preferences.

The persisted Search Strategy is the authoritative operational state.


## 10. Source Connector Architecture

Opportunity sources vary significantly.

Each source should therefore be accessed through a connector abstraction.

Conceptually:

    SourceConnector

        discover()
        fetch()
        normalize()

Exact interfaces will be refined during implementation.

Possible connector implementations include:

    ApiSourceConnector
    HttpSourceConnector
    BrowserSourceConnector
    FeedSourceConnector

Source-specific implementations may extend one of these approaches.

For example:

    FAOSourceConnector
    UNOPSSourceConnector
    WorldBankSourceConnector
    ADBSourceConnector

The core application must not depend on source-specific page structures.


## 11. Acquisition Strategy

For each source, prefer the least complex reliable acquisition mechanism.

Order of preference:

1. official documented API/feed;
2. official structured public endpoint;
3. direct HTTP retrieval and parsing;
4. browser automation.

Browser automation should be introduced only where necessary.

A connector should record enough diagnostic information to determine whether
a scan succeeded, partially succeeded, or failed.

**Implemented connectors (Phase 6 / Phase 12):** each connector acquires source
records, maps them to `RawOpportunity`, and is orchestrated by a source-specific
scan service that records `SourceScan` and invokes the shared Phase 5–7 pipeline
(and Phase 8 when production AI is configured). Source-specific normalizers run
at processing time, not inside connectors.

- **FAO Jobs** — `FaoJobsConnector` via the public Oracle Taleo Career Section
  JSON endpoint ``POST /careersection/rest/jobboard/searchjobs`` (session from
  the public job search page). `FaoOpportunityNormalizer`.
- **DevelopmentAid Jobs** — `DevelopmentAidJobsConnector` via the site's
  frontend JSON API ``POST /api/frontend/job/search`` and
  ``GET /api/frontend/job/{id}`` for full HTML descriptions (no account required
  for search/detail in current use). `DevelopmentAidOpportunityNormalizer`.
  **Rate limiting:** the public detail API returns ``X-RateLimit-Limit: 20``
  (observed 2026-09-29). With ``fetch_details: true``, the connector fetches
  details **sequentially** with a default **3s** pause between detail GETs, bounded
  **HTTP 429** retries (``Retry-After`` when present, else exponential backoff),
  and early stop after sustained throttling. List-level rows are still mapped when
  detail fails (`PARTIAL` scan, aggregated operator warning). **Phase 17C-2:**
  detail JSON sectors, languages, experience, organisation type, contract type,
  application `url`, and `lastUpdated` are mapped into source-neutral
  `structured_facts` on `RawOpportunity.extra` (not new opportunity columns);
  Phase 8 prompt text and content digest include these facts from the latest raw
  observation; listing vs application URLs are stored on `opportunity_sources`.
- **World Bank procurement notices** — `WorldBankProcNoticesConnector` via
  documented ``GET search.worldbank.org/api/v2/procnotices`` JSON (public, no
  auth). Stable `id` (e.g. `OP00471368`); detail URL on projects.worldbank.org.
  `WorldBankOpportunityNormalizer`. Broad notice retrieval; relevance is decided
  downstream (no semantic profile filters in the connector).
- **ReliefWeb Jobs** — `ReliefWebJobsConnector` via documented
  ``POST https://api.reliefweb.int/v2/jobs?appname=…`` (pre-approved appname in
  ``JOBHUNTER_RELIEFWEB_APPNAME``). Full job ``body`` in API response;
  `ReliefWebOpportunityNormalizer`. Listing URL on reliefweb.int; optional
  external application URL in `structured_facts`.
- **TED EU procurement** — `TedProcurementConnector` via anonymous
  ``POST https://api.ted.europa.eu/v3/notices/search`` (expert query).
  `TedOpportunityNormalizer`. Stable id: TED ``publication-number``.
- **UNDP Jobs** — `UndpJobsConnector` via official all-vacancies RSS
  ``jobs.undp.org/rss_feeds/rss.xml`` (RSS 0.91; Oracle requisition id in
  link). `UndpOpportunityNormalizer`. Feed summaries are partial; deadlines
  parsed from feed HTML snippets.
- **AfDB consultant opportunities** — `AfdbConsultantsConnector` via official
  consultants RSS (requires descriptive User-Agent). Optional detail-page
  enrichment for closing dates and longer descriptions. Stable AfDB node id in
  `guid`. `AfdbOpportunityNormalizer`.
- **ADB CSRN consulting opportunities** — `AdbCsrnConnector` via public Oracle
  HTML on ``selfservice.adb.org`` (CSRN home listing; cookie session for
  pagination). Stable notice id ``E-…-…`` in `source_reference`. List fields
  only: `fetch_details` is ignored (CSRN notice body uses Oracle popup flow).
  `source_url` = CSRN listing anchor; `structured_facts.application_url` =
  ``https://csrn.adb.org/``. `AdbCsrnOpportunityNormalizer`.

**Scan services (Phase 17B):** explicit per-source services remain
(`FaoScanService`, `DevelopmentAidScanService`, `WorldBankScanService`,
`UndpScanService`, `AfdbScanService`, `AdbScanService`) — structural duplication is acceptable;
behaviour and audit semantics are preserved without a generic refactor.

Additional sources should follow the same pattern: connector + scan service +
normalizer; no duplicate eligibility, assessment, or ranking pipelines.

**SourceScan:** each scan run is recorded in `source_scans` with
start/completion time, status (`SUCCESS`, `PARTIAL`, `FAILED`, `RUNNING`),
counts of records retrieved/processed/failed, and optional error summary text.
This is scan-level provenance, not a scheduling or monitoring platform.


## 12. Raw and Normalized Data

The system should distinguish between retrieved source information and
normalized application information.

Conceptually:

    Source
      │
      ▼
    RawOpportunity
      │
      ▼
    Normalizer
      │
      ▼
    Opportunity

Raw information should be retained sufficiently to:

- diagnose parsing problems;
- reprocess information;
- verify provenance;
- detect source changes.

The exact raw-data retention strategy should balance traceability and storage
requirements.

**Phase 5 boundary:** source connectors acquire source information and map it
into `RawOpportunity`. The source-independent processing pipeline owns
normalization into the canonical `Opportunity` representation. Connectors must
not embed the canonical processing pipeline.

Each processing run retains append-only `RawOpportunity` rows and records an
`OpportunityObservation` linking the raw evidence to the canonical opportunity.


## 13. Deduplication

The same opportunity may appear:

- repeatedly on the same source;
- on multiple source pages;
- on aggregator sites;
- on both an organisation's site and a procurement portal.

Deduplication should therefore use multiple signals.

Potential signals include:

1. authoritative source identifier;
2. canonical URL;
3. organisation + reference number;
4. title + organisation + deadline;
5. normalized textual similarity;
6. AI-assisted comparison only where deterministic methods remain ambiguous.

The authoritative/original source should be preferred where identifiable.

Duplicate source references should be retained rather than discarded.


## 14. Change Detection

Known opportunities should be compared with previous observations.

Material changes may include:

- deadline;
- Terms of Reference;
- title;
- location;
- eligibility;
- duration;
- status.

The system should distinguish at least:

- NEW;
- UPDATED;
- STILL OPEN;
- CLOSED/EXPIRED.

Change history should be retained where useful.

**Phase 5 implementation:** `OpportunityObservation` is append-only processing
evidence (one row per processed `RawOpportunity`, idempotent on re-processing
the same raw id). `OpportunityChange` is a lightweight audit of material field
changes detected during processing (not a generic event store).
`Opportunity.lifecycle_status` reflects the outcome of the latest processing
run; history remains on observations and change records.


## 15. Filtering Architecture

Filtering is performed progressively.

### Stage 1: deterministic eligibility

Examples:

- deadline passed;
- explicit nationality mismatch;
- explicit local-only requirement;
- internship;
- volunteer assignment;
- explicitly junior position.

### Stage 2: interpreted eligibility

Used where requirements are ambiguous.

Example:

    "National specialist preferred"

may require contextual interpretation rather than automatic rejection.

### Stage 3: professional relevance

Determine whether the actual nature of the opportunity falls within or near
the desired professional scope.

### Stage 4: profile matching

Determine how strongly professional evidence supports the requirements.

The system must preserve the reason for exclusion or reduced relevance.

**Phase 7 (deterministic eligibility):** evaluates normalized opportunities
against the active `SearchStrategyRevision` (exclusions and `HARD_CONSTRAINT`
criteria only—not themes or `PREFERENCE` criteria). Rule outcomes use
TRUE/FALSE/UNKNOWN tri-state semantics where appropriate. Aggregate
`EligibilityStatus` meanings: `INELIGIBLE` (clear fail or EXPIRED/CLOSED
lifecycle), `ELIGIBLE` (may continue— not a quality match), `REVIEW_REQUIRED`
(suggestive but inconclusive evidence), `UNKNOWN` (insufficient information
without specific concern). `ProfessionalProfile` is not used in Phase 7.
**Phase 8 (AI profile / relevance assessment):** produces one append-only
`OpportunityProfileAssessment` per evaluation run, with logical sections for
professional relevance and profile matching. It uses `ProfessionalProfile`
evidence (via deterministic context selection), the active
`SearchStrategyRevision` (themes and `PREFERENCE` criteria only—not as
professional evidence), and Phase 7 rule summaries where interpretation is
still needed. Output uses **ordinal** relevance and alignment classifications,
not numeric 0–100 scores. It does not decide whether to apply.

Interpreted eligibility concerns identified in Phase 8 are recorded in the
assessment; deterministic eligibility remains Phase 7.


## 16. AI Assessment Architecture

Phase 8 persists a structured `OpportunityProfileAssessment` (JSON result plus
metadata). A successful assessment includes, among other fields:

- `overall_relevance` (ordinal band);
- `source_data_sufficiency` (e.g. `LIST_SUMMARY_ONLY` for sparse list summaries);
- `professional_relevance` (scope, delivery mode and seniority **inferences**);
- grounded `service_alignments`, `assignment_evidence`, `capability_evidence`,
  `skill_evidence`, `language_evidence`, `country_evidence` (profile entity ids
  from the context pack only);
- `theme_alignments` and `preference_notes` (strategy interpretation);
- `interpreted_eligibility` (Phase 7 UNKNOWN / review-oriented rules);
- `strengths`, `gaps`, `uncertainties`, `rationale`.

Each grounded item uses `basis`: `OPPORTUNITY_FACT`, `PROFILE_FACT`, or
`INFERENCE`. Opportunity excerpts must be substrings of supplied opportunity
fields.

**Numeric dimension scores and final priority ranking are Phase 9**, not Phase 8.

AI responses used by application logic must be validated against a structured
schema; malformed or ungrounded output must not become trusted assessment data.


## 17. Ranking Architecture

Ranking is separate from profile matching.

Profile matching asks:

    "How well does Jan's documented professional evidence match this
    opportunity?"

Ranking asks:

    "Given professional fit AND Jan's current search strategy, how much
    attention should this opportunity receive?"

Conceptually:

    ranking =
        profile match
        + professional service alignment
        + current strategic priorities
        + assignment preference
        + eligibility
        + other configurable factors

The ranking algorithm should be deterministic where possible after AI-derived
assessment dimensions have been generated.

Ranking weights must be configurable.

The stored ranking should include an explanation of the important contributing
factors.

**Phase 9 (deterministic ranking_v1):** `OpportunityRankingService` consumes
successful production `OpportunityProfileAssessment` results (excluding
`model_provider=fake` in normal operation) and the active
`SearchStrategyRevision`. No LLM calls. Internal integer points in
`ranking_config_v1` drive ordering; user-facing output is priority bands
(`HIGH`, `MEDIUM`, `LOW`, `REVIEW`) plus `RankingFactor` explanations.
`UNRANKED` / `EXCLUDED` are statuses, not bands. Rank position is derived
dynamically when listing candidates (no persisted `rank_sequence`).
`LIST_SUMMARY_ONLY` adds warnings and a modest score penalty but does not cap
priority bands. Append-only `OpportunityRanking` rows reference eligibility and
assessment FKs and an `input_digest` for idempotency.


## 18. Persistence Architecture

### Primary database

PostgreSQL is the preferred persistent database.

Reasons:

- robust relational model;
- appropriate for persistent server deployment;
- strong support for structured and semi-structured data;
- mature Python integration;
- full-text search capability;
- JSON/JSONB support;
- future vector-search capability if required;
- already familiar to the user.

SQLite may be used for isolated tests or lightweight local development where
appropriate, but should not define the production architecture.

### Documents

Documents include:

- CV;
- Professional Services document;
- Terms of Reference;
- generated CVs;
- generated cover letters;
- other application documents.

Binary documents should not unnecessarily be stored directly in relational
database columns.

The initial implementation may use filesystem/object storage abstraction, with
the exact deployment storage mechanism decided later.


## 19. Initial Domain Entities

The initial conceptual domain model includes:

    ProfessionalProfile
    ProfileDocument
    ProfessionalService
    Capability
    Assignment
    AssignmentCapability
    Skill
    LanguageCapability
    CountryExperience

    SearchStrategy
    SearchStrategyRevision
    SearchTheme
    StrategyCriterion
    ExclusionCriterion

    JobSource
    SourceScan
    RawOpportunity

    Opportunity
    OpportunitySource
    OpportunityObservation
    OpportunityChange

    EligibilityDecision
    EligibilityRuleResult
    OpportunityProfileAssessment
    OpportunityRanking
    OpportunityReviewRecord

    OpportunityFeedback

    Application
    ApplicationEvent
    GeneratedDocument

These are conceptual entities.

They do not imply that every entity must immediately become a separate
database table.


## 20. AI Provider Abstraction

Application/domain logic should not directly depend on a specific LLM provider.

Use an application-level AI interface.

Phase 8 introduces an `AssessmentModel` port (e.g. `assess(request)` returning
validated structured JSON). Provider-specific implementations (OpenAI, fake/test)
sit in infrastructure. Model id and API credentials are configuration
(`JOBHUNTER_OPENAI_MODEL`, `JOBHUNTER_OPENAI_API_KEY`); no vendor SDK in
domain/application code.

Future capabilities may extend the same pattern:

        interpret_strategy_change(...)
        generate_cover_letter(...)
        tailor_cv(...)

Provider-specific implementations sit behind application ports.

This allows model choice to evolve independently from the core domain model.

The initial model/provider will be selected during implementation based on:

- structured-output capability;
- reasoning quality;
- context capacity;
- cost;
- API availability;
- reliability.


## 21. AI Context Construction

Do not send the complete database or all historical information to the AI
model for every assessment.

Construct task-specific context.

For profile matching, relevant context may include:

- opportunity requirements;
- professional-service definitions;
- relevant profile attributes;
- selected relevant assignments;
- languages;
- current search strategy.

Context construction should be explicit and testable.

Future retrieval mechanisms may be introduced if required.

Vector search or a dedicated vector database is not required initially.


## 22. Application Backend

The application backend should be implemented in Python.

Reasons include:

- strong AI ecosystem;
- strong HTTP/parsing/browser automation ecosystem;
- strong PostgreSQL support;
- document-processing ecosystem;
- existing user expertise;
- suitability for scheduled processing and data analysis.

The exact Python web/application framework should be selected before
implementation begins.

The initial architecture does not require separate backend services.


## 23. User Interface

The initial UI should prioritise functionality over visual complexity.

Required areas eventually include:

- dashboard;
- opportunity list;
- opportunity detail;
- filtering/sorting;
- source management;
- search criteria management;
- professional profile;
- current search strategy;
- strategy history;
- feedback;
- application tracking;
- conversational strategy interface.

A lightweight Python UI framework is appropriate for the initial version.

Streamlit is a strong candidate for the Bootcamp implementation because:

- development is rapid;
- it integrates naturally with Python;
- it supports tables and dashboards well;
- it is adequate for a personal single-user application.

The UI architecture should nevertheless avoid placing core business logic
inside UI components.

Phase 10 implements a Streamlit dashboard under `src/jobhunter/ui/streamlit/`.
Pages call application services in `jobhunter.application.review` (summary,
queue, detail, human review). Read paths do not persist rankings or
assessments. Human review uses append-only `OpportunityReviewRecord` rows,
separate from eligibility, assessment, and ranking outputs.

Phase 11 adds conversational search strategy management via
`jobhunter.application.strategy_conversation` and a Streamlit strategy page.
Natural-language instructions are interpreted through a `StrategyChangeModel`
port (OpenAI or explicit fake for tests). Structured mutations are validated
and shown as a diff; only user confirmation activates a new immutable
`SearchStrategyRevision` with `RevisionChangeSource.CONVERSATION_CONFIRMED`.

Phase 15 extends the dashboard for operators:

- **Search strategy display** — `jobhunter.application.strategy_display` builds
  tabular presentation DTOs from `ActiveStrategyView` (themes, preferences, hard
  constraints, exclusions) with human-readable labels; canonical strategy data
  remains in revision snapshots.
- **Structured strategy edits** — `StructuredStrategyEditService` applies the
  same deterministic `apply_mutations` path as conversational proposals, without
  an LLM; confirmation uses `RevisionChangeSource.STRUCTURED_EDIT`.
- **Navigation** — `ui/streamlit/navigation.py` and query parameters link Home
  counts to filtered Opportunities and to
  `opportunity_detail?opportunity_id=…` (also used in HIGH alert emails via
  `build_opportunity_dashboard_url`).
- **Sources** — `jobhunter.application.sources` is registry-driven
  (`registry.py`); operational acquisition settings remain in
  `automation.json` and do **not** create `SearchStrategyRevision` rows.
  Scan health and opportunity link counts come from PostgreSQL.

**Configuration separation (enforced conceptually):**

| Concern | Question | Persistence | Creates strategy revision? |
|--------|----------|-------------|----------------------------|
| Search strategy | What opportunities do I want? | `SearchStrategyRevision` | Yes |
| Source configuration | Where/how broadly to scan? | `automation.json` (+ connector code) | No |
| Automation | When/how to run and notify? | `automation.json`, worker env | No |

Phase 16 adds structured **assessment operator presentation**
(`application/review/assessment_presentation.py`) with explicit situations
(no production assessment, fake-only, ineligible gate, failed attempt, sparse
but valid JSON for `LIST_SUMMARY_ONLY` / `PARTIAL`). Raw persisted JSON
remains available in a collapsed diagnostic expander. Shared enum labels live
in `application/display_labels.py`.

**Future connectors:** register metadata in `application/sources/registry.py`,
add `KNOWN_SOURCE_KEYS` / `SOURCE_KEY_TO_JOB_SOURCE_ID`, and a `sources` entry
in `automation.json`; the Sources UI lists registered connectors without
hard-coding a fixed pair.


## 24. Scheduling

The system must eventually run independently of the user's local computer.

Scheduled scans should be possible, for example:

    Monday   08:00 Europe/Amsterdam
    Thursday 08:00 Europe/Amsterdam

Scheduling must invoke application services rather than UI code.

The scheduler should support:

- scan execution;
- failure logging;
- result aggregation;
- notification triggering.

**Phase 13:** scheduling semantics and pipeline configuration live in JSON
(`config/automation.example.json`, path override via `JOBHUNTER_AUTOMATION_CONFIG`).
An external scheduler (cron, Synology Task Scheduler, Docker `schedule`, etc.) should
invoke `scripts/run_scheduled_pipeline.py --apply-if-due` or `--apply` once and
exit. The application does not embed a long-running scheduler process.

`ScheduledPipelineOrchestrator` coordinates registered source scan adapters (FAO,
DevelopmentAid, …), optional production OpenAI assessment, Phase 9 ranking,
HIGH-band opportunity alert evaluation, and end-of-run summary notification.
Each full execution is audited in `automation_runs` with links to per-source
`source_scans` rows.

Worker sequence (conceptual): scan → normalize/process → eligibility → production
assessment → deterministic ranking → **opportunity alert evaluation** → run
summary notification. A failure sending one HIGH alert does not abort processing
of other opportunities; failures are recorded in `opportunity_notifications` and
surfaced in run warnings.

### Synology production deployment

Production on a Synology NAS uses standalone `docker-compose.prod.yml` (external
PostgreSQL, no merge/`!reset` with the dev compose file):

```text
Internet → DSM HTTPS reverse proxy (jobhunter.jvbgis.com)
         → edge (Caddy, localhost:8080 only)
              /     → static landing (no database)
              /app  → Caddy HTTP basic auth → Streamlit (internal, baseUrlPath /app)
```

- **PostgreSQL** remains an **external** server (`JOBHUNTER_DATABASE_URL`); no
  database container on the NAS.
- **Worker** and **migrate** are one-shot Compose services; Synology Task Scheduler
  invokes the worker every ~15 minutes with `--apply-if-due`.
- **Trust boundary:** only the edge port is exposed to DSM; Streamlit port 8501 is
  not published on the host.
- **Authentication** for `/app` is Caddy HTTP basic auth (bcrypt hash in `.env`);
  JobHunter does not implement user management.
- **Production guards:** `JOBHUNTER_ENV=production` requires SMTP when notifications
  are enabled; worker `--apply` uses a PostgreSQL advisory lock to prevent duplicate
  concurrent runs.

See [deployment.md](deployment.md) for operational steps.


## 25. Notifications

Phase 13 introduces `NotificationSender` with `ConsoleNotificationSender` and
`SmtpNotificationSender` (SMTP when `JOBHUNTER_SMTP_*` is configured).

Two notification kinds share the same transport abstraction:

1. **Scheduled run summary** — aggregated counts and highlights from persisted
   state at the end of a worker run (MEDIUM opportunities may appear here).
2. **Immediate HIGH opportunity alert** — one email per newly produced production
   ranking that satisfies the alert policy (see below).

Notification bodies are built from persisted JobHunter state only; no extra LLM
calls for email text.

### HIGH immediate alert policy

An immediate alert is sent only when all of the following hold:

- opportunity lifecycle is actionable (not `CLOSED` or `EXPIRED`);
- eligibility is not `INELIGIBLE`;
- latest applicable ranking state is `RANKED` with band **HIGH** (`ranking_v1`);
- linked profile assessment is production (`model_provider` is not `fake`);
- the ranking outcome from the current worker pass is **new** (`reused` is false —
  no retroactive blast for historical HIGH rows when the feature is deployed);
- no prior **successful** delivery exists for this ranking state.

LOW-band opportunities are dashboard-only. MEDIUM-band opportunities are not
emailed immediately but may still appear in the scheduled run summary.

### Duplicate suppression and retry

Alert identity is tied to the ranking row, not merely `opportunity_id`:

- `notification_key` = `high_ranking:{ranking_id}` (unique in
  `opportunity_notifications`).

A successful send (`status` = `SENT`) suppresses duplicate delivery for that key.
A failed send (`status` = `FAILED`, `error_summary` set) remains auditable and is
retried on a later worker pass until it succeeds or the policy no longer applies.
A materially new append-only ranking that is again HIGH may produce a new alert
with a new key.

Optional dashboard links in alert email use `JOBHUNTER_WEB_BASE_URL` when set
(site root or `/app` suffix; application code normalises to `/app/?opportunity_id=…`).

In production, when `JOBHUNTER_ENV=production` and notifications are enabled,
SMTP must be configured; console fallback is not used for worker delivery.

### Run summary content

A scan report may contain:

- new high-ranking opportunities (summary context);
- materially updated opportunities;
- still-open high-priority opportunities;
- failed source scans;
- link to the dashboard.

Notification generation must use persisted scan results rather than repeating
the search independently.


## 26. Export

Opportunity lists should support export to XLSX.

Export should operate on normalized persisted opportunity data.

Useful export fields may include:

- title;
- organisation;
- country;
- deadline;
- source;
- URL;
- search theme;
- eligibility;
- relevance;
- profile-match score;
- ranking;
- lifecycle status;
- application status;
- remarks.


## 27. Application Tracking (Phase 14)

Application / **pursuit** tracking is separate from opportunity lifecycle,
eligibility, AI assessment, ranking, and **review triage** (SHORTLIST /
INVESTIGATE / DISMISS).

| Mechanism | Question |
|-----------|----------|
| Review triage | Should I consider this opportunity? |
| Pursuit tracking | What am I doing after I decide to pursue it? |

Pursuit is started only by an explicit human action (**Start pursuing**).
SHORTLIST does not create pursuit records.

### Pursuit status model

Append-only `opportunity_pursuit_status_events` record transitions. Current
status is the latest event by `(recorded_at desc, id desc)`. Operational
fields (submission deadline, next action, contacts, submission URL, reference)
live on `opportunity_pursuits` as the current working copy with
`operational_updated_at` (not a full audit trail of every edit).

Statuses (`PursuitStatus`):

- `CONSIDERING` — initial when pursuit starts
- `PREPARING` — EOI/proposal preparation
- `SUBMITTED` — EOI or proposal submitted
- `CLIENT_SHORTLISTED` — client/procurement shortlist (**not** review SHORTLIST)
- `INTERVIEW`, `NEGOTIATION`
- Terminal: `AWARDED`, `NOT_AWARDED`, `WITHDRAWN`

Stage skipping is allowed (e.g. `CONSIDERING` → `SUBMITTED`). Terminal states
block further transitions.

### UI

- **Applications** page — active/completed pursuit work queue
- **Opportunity detail** — pursuit panel alongside existing review form

Deferred: email/calendar reminders, automatic submission, EOI/proposal generation
(Phase 15+).


## 28. Personalisation Architecture

Personalisation is downstream of human opportunity selection.

Conceptually:

    Selected Opportunity
             +
    Professional Evidence
             +
    Source CV
             │
             ▼
      Personalisation Service
             │
       ┌─────┴─────┐
       ▼           ▼
    Tailored CV   Cover Letter

Generated content must remain grounded in professional evidence.

The user must review final generated documents before external submission.


## 29. Security Architecture

Secrets must be external to source control.

Examples:

- database credentials;
- AI API keys;
- SMTP/email credentials;
- source credentials.

Use environment variables or an appropriate deployment secrets mechanism.

The repository may contain:

    .env.example

but never:

    .env

with actual credentials.

Authenticated external sources should use separate credential configuration
from ordinary source metadata.


## 30. Deployment Architecture

The production system must operate independently of the user's local laptop.

The preferred initial deployment model is a small Linux virtual server
running containerised application components.

Conceptually:

    Internet
       |
       v
    Reverse Proxy / HTTPS
       |
       v
    +--------------------------------+
    | Linux VPS                      |
    |                                |
    | Docker                         |
    |                                |
    | +----------------------------+ |
    | | JobHunter Web/UI           | |
    | +----------------------------+ |
    |                                |
    | +----------------------------+ |
    | | JobHunter Worker           | |
    | | scheduled scans            | |
    | | source acquisition         | |
    | | AI processing              | |
    | +----------------------------+ |
    |                                |
    | +----------------------------+ |
    | | PostgreSQL                 | |
    | +----------------------------+ |
    |                                |
    | Persistent document storage   |
    +--------------------------------+

The application should be accessible through HTTPS, potentially using a
dedicated subdomain such as:

    jobhunter.jvbgis.com

Docker is the preferred packaging and deployment mechanism.

Docker Compose is appropriate for the initial single-server deployment.

JobHunter is intended to support two cooperating runtime modes on shared
PostgreSQL persistence:

1. an interactive web process (Streamlit dashboard, review, strategy
   management); and
2. background worker processes for scheduled source acquisition and downstream
   processing (normalize, eligibility, assessment, ranking).

Scheduled scans and pipeline execution must not depend on an active Streamlit
session. The Phase 13 worker (`run_scheduled_pipeline.py`) invokes the same
application services as per-source CLI scans, with explicit flags for production
assessment and ranking.

**Deployment packaging:** one Docker image serves Streamlit and the worker CLI.
Synology (or cron) invokes `docker compose run --rm worker` on a short interval;
`--apply-if-due` opens on Mon/Thu from 08:00 Europe/Amsterdam (polled ~every
15 minutes) and skips once a SCHEDULED SUCCESS/PARTIAL run exists that day.
Notifications use `NotificationSender`: SMTP when `JOBHUNTER_SMTP_*` env vars are
set, otherwise console output for logs. See [deployment.md](deployment.md).

The architecture should not depend on a specific VPS/cloud provider.

A provider such as Hetzner Cloud is a suitable initial deployment candidate,
but provider selection remains a deployment decision rather than an
application architecture dependency.

The architecture should permit later migration to managed database,
object-storage, application-platform, or cloud services if operational
requirements justify it.


## 31. Development and Deployment Flow

The expected development and deployment flow is:

    C:\DEV\job-hunting
            |
            | git push
            v
          GitHub
            |
            | deploy
            v
       Linux VPS / Docker
       jobhunter.jvbgis.com

Development takes place locally in the repository using Cursor.

The application and PostgreSQL should be capable of running locally using
Docker Compose where practical.

Continuous integration and continuous deployment are not required for the
initial vertical slice. They may be introduced later once the application is
stable enough to benefit from automated testing and deployment.


## 32. Repository Structure

Initial target structure:

    job-hunting/
    │
    ├── AGENTS.md
    │
    ├── README.md
    │
    ├── src/
    │   └── jobhunter/
    │       ├── domain/
    │       ├── application/
    │       ├── infrastructure/
    │       ├── connectors/
    │       ├── ai/
    │       └── ui/
    │
    ├── tests/
    │
    ├── docs/
    │   └── architecture.md
    │   └── implementation-plan.md
    │
    ├── data/
    │   └── fixtures/
    │
    ├── scripts/
    │
    ├── .env.example
    ├── .gitignore
    └── pyproject.toml

Responsibilities:

### domain/

Core domain models and rules.

Must not depend on UI, external websites, or concrete AI providers.

### application/

Use cases and orchestration of domain behaviour.

Examples:

- run scan;
- process opportunity;
- assess opportunity;
- update search strategy;
- record feedback.

### infrastructure/

Persistence, configuration, document storage, scheduling, email, and other
technical infrastructure.

### connectors/

External opportunity-source integrations.

### ai/

AI interfaces, prompt construction, structured schemas, and provider adapters.

### ui/

User-interface code.

Business rules must not be implemented exclusively in this layer.


## 33. Dependency Direction

Preferred dependency direction:

    UI
     │
     ▼
    Application
     │
     ▼
    Domain

Infrastructure implements interfaces required by the application/domain.

External systems should therefore sit at the edges:

    External Sources
          │
       Connector
          │
          ▼
       Application
          │
          ▼
        Domain
          ▲
          │
    Persistence Adapter
          │
       PostgreSQL

The core domain should remain testable without live external services.


## 34. Error Handling

Failures should be isolated where practical.

For example:

- failure of one source must not prevent other sources from scanning;
- failure of AI assessment must not lose the acquired opportunity;
- notification failure must not invalidate scan results;
- document-generation failure must not change application status.

Errors should be logged with sufficient context for diagnosis.


## 35. Testing Architecture

Testing should include:

### Unit tests

For:

- domain rules;
- filters;
- normalization;
- ranking;
- lifecycle;
- change detection.

### Connector tests

Use stored representative source responses where practical.

Avoid depending exclusively on live websites.

### Persistence tests

Verify repository/database behaviour.

### AI contract tests

Verify:

- context construction;
- structured request/response schemas;
- handling of invalid AI output;
- provider abstraction.

Tests should not require paid AI calls unless explicitly designated as
integration tests.


## 36. Observability

The system should record operational information for each scan.

Examples:

    scan id
    start time
    end time
    source
    source status
    records retrieved
    new opportunities
    updated opportunities
    excluded opportunities
    assessment failures
    errors

This information should eventually be visible through the dashboard.


## 37. Initial Technology Direction

The initial preferred technology direction is:

| Concern | Initial direction |
|---|---|
| Language | Python |
| Architecture | Modular monolith |
| Database | PostgreSQL |
| ORM / persistence | SQLAlchemy 2.x (synchronous), psycopg 3, Alembic |
| UI | Streamlit candidate |
| AI | Provider abstraction; provider/model TBD |
| HTTP acquisition | Python HTTP client |
| HTML parsing | Python parsing library |
| Browser automation | Playwright candidate, only where required |
| Scheduling | Deployment-dependent |
| Documents | Files/object-storage abstraction |
| XLSX | Python XLSX library |
| Testing | pytest |
| Packaging | Docker / Docker Compose |
| Source control | Git / GitHub |
| Deployment | Linux VPS; Hetzner Cloud suitable candidate |

Technology candidates are not dependencies until accepted and introduced by
an implementation phase.


## 38. Deferred Decisions

The following decisions are deliberately deferred:

- concrete Python web/backend framework;
- exact Streamlit architecture;
- AI provider and models;
- embedding model;
- whether vector search is required;
- browser automation implementation;
- scheduler;
- email provider;
- object/document storage;
- production VPS/cloud provider;
- authentication model;
- backup strategy;
- CI/CD mechanism.

These decisions should be made when their implementation phase approaches,
rather than introducing infrastructure prematurely.


## 39. Initial Vertical Slice

The first useful end-to-end implementation should be deliberately small.

Target:

    One Opportunity Source
              │
              ▼
            Fetch
              │
              ▼
           Normalize
              │
              ▼
          PostgreSQL
              │
              ▼
           Filter
              │
              ▼
         AI Assessment
              │
              ▼
            Rank
              │
              ▼
       Minimal Dashboard

The first vertical slice should demonstrate the architectural boundaries before
additional sources or advanced functionality are introduced.

It should use a source that can be accessed reliably without complicated
authentication.


## 40. Evolution

The architecture is expected to evolve.

Changes should be driven by demonstrated requirements discovered during
implementation and actual use.

Significant architectural changes should:

1. identify the problem;
2. describe the proposed change;
3. explain the trade-off;
4. update this document;
5. then be implemented.

Avoid redesigning the architecture merely because another technology or
framework becomes fashionable.
