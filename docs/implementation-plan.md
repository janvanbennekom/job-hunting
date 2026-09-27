# implementation-plan.md

## 1. Purpose

This document defines the incremental implementation plan for the Job Hunting
AI Agent.

It translates the target architecture in `docs/architecture.md` into bounded
development phases suitable for implementation with Cursor.

The plan is intentionally incremental.

Each phase should:

- have a clearly defined scope;
- produce a testable result;
- preserve a working repository;
- avoid implementing functionality assigned to later phases;
- validate important architectural assumptions before additional complexity
  is introduced.

The implementation sequence may evolve as requirements become clearer.

Changes to the plan must remain consistent with `AGENTS.md` and
`docs/architecture.md`.


## 2. Development Method

Development follows a controlled iterative workflow:

    Requirement / Next Step
             |
             v
        ChatGPT Review
             |
             v
       Cursor Prompt
             |
             v
    Cursor Implementation
             |
             v
       Run / Test / Review
             |
             v
        ChatGPT Review
             |
       +-----+------+-----------+
       |            |           |
       v            v           v
     ACCEPT        FIX       INVESTIGATE
       |
       v
    Next Step

ChatGPT acts primarily as:

- architecture assistant;
- implementation planner;
- Cursor prompt designer;
- implementation reviewer;
- test/result reviewer;
- next-step advisor.

Cursor acts primarily as:

- repository-aware coding agent;
- implementation agent;
- refactoring agent when explicitly requested;
- test-writing and test-execution agent;
- documentation updater.

The user remains responsible for accepting significant design decisions and
changes to scope.


## 3. Phase Structure

The planned phases are:

| Phase | Name |
|---|---|
| 0 | Repository and Development Foundation |
| 1 | Core Domain Model |
| 2 | Persistence Foundation |
| 3 | Professional Profile |
| 4 | Search Strategy and Preferences |
| 5 | Opportunity Processing Foundation |
| 6 | First Real Source Connector |
| 7 | Filtering and Eligibility |
| 8 | AI Relevance and Profile Matching |
| 9 | Ranking and Explainability |
| 10 | Minimal Dashboard |
| 11 | Conversational Strategy Management |
| 12 | Multi-Source Expansion |
| 13 | Scheduling and Notifications |
| 14 | Application Tracking |
| 15 | CV and Cover-Letter Personalisation |
| 16 | XLSX Export and Operational Features |
| 17 | Deployment |
| 18 | Hardening and Further Evolution |

Phases may contain multiple bounded implementation steps.

Do not assume that an entire phase should be implemented in one Cursor prompt.

## 3.1 Bootcamp MVP and Product Roadmap

The phases in this document describe the intended evolution of JobHunter.
They are not all part of the initial AI Maker Bootcamp implementation.

### Bootcamp MVP — JobHunter V0.1

The primary Bootcamp objective is to implement and demonstrate the first end-to-end vertical slice of JobHunter.

The target is:

    One Real Opportunity Source
              |
              v
            Acquire
              |
              v
           Normalize
              |
              v
          PostgreSQL
              |
              v
            Filter
              |
              v
       AI Profile Matching
              |
              v
             Rank
              |
              v
      Minimal Dashboard

This corresponds broadly to Phases 0–10.

For the Bootcamp MVP, Phase 6 is deliberately limited to one real opportunity source. The objective is to prove the architecture and the AI-assisted opportunity-assessment workflow, not to achieve broad source coverage.

### Post-Bootcamp Roadmap

The following capabilities are part of the longer-term product roadmap and are not required for the Bootcamp MVP:

- conversational strategy management;
- broad multi-source coverage;
- scheduled autonomous execution;
- email notifications;
- application tracking;
- CV personalisation;
- cover-letter generation;
- XLSX export and additional operational features;
- production deployment;
- hardening and advanced capabilities.

These remain part of the target architecture and may be implemented
incrementally after the MVP has been validated.

### Scope Discipline

Bootcamp development should prioritise a complete, demonstrable vertical slice over breadth of functionality.

Functionality from later phases must not be introduced merely because it appears in the roadmap.

After the MVP is operational, its architecture, usability, matching quality, and development experience should be reviewed before deciding which post-Bootcamp capabilities to implement next.


# Phase 0 — Repository and Development Foundation

## Objective

Create a clean, reproducible project foundation without implementing JobHunter business functionality.

## Scope

Create the initial repository structure:

    job-hunting/
    │
    ├── AGENTS.md
    ├── README.md
    ├── pyproject.toml
    ├── .gitignore
    ├── .env.example
    │
    ├── docs/
    │   ├── architecture.md
    │   └── implementation-plan.md
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
    ├── data/
    │   └── fixtures/
    └── scripts/

Configure:

- Python project metadata;
- dependency management;
- pytest;
- basic logging;
- environment-variable configuration;
- development conventions;
- Git exclusions.

Create a minimal importable `jobhunter` package.

## Deliberately excluded

Do not yet implement:

- database models;
- PostgreSQL;
- source connectors;
- AI integration;
- Streamlit;
- browser automation;
- scheduling;
- application tracking.

## Verification

The phase is complete when:

- project installs successfully in the development environment;
- `jobhunter` can be imported;
- pytest executes successfully;
- a minimal smoke test passes;
- secrets and local environment files are excluded from Git;
- repository structure follows the architecture.


# Phase 1 — Core Domain Model

## Objective

Define the core technology-independent domain concepts before introducing
database or UI concerns.

## Initial concepts

Implement domain representations for the minimum set needed to describe:

- JobSource;
- RawOpportunity;
- Opportunity;
- OpportunitySource;
- opportunity lifecycle status;
- opportunity type;
- eligibility state.

Use simple Python domain models.

The exact representation should be selected during implementation based on
clarity, validation needs, and maintainability.

## Key principles

Domain objects must not depend on:

- PostgreSQL;
- ORM libraries;
- Streamlit;
- external websites;
- AI providers.

Important identifiers and timestamps should be explicit.

## Tests

Test:

- object construction;
- validation;
- status values;
- important invariants;
- serialization where required.

## Deliverable

A tested core domain package capable of representing an opportunity and its
source independently from persistence or acquisition.


# Phase 2 — Persistence Foundation

## Objective

Introduce PostgreSQL persistence while preserving separation between domain
logic and infrastructure.

## Scope

Select and configure:

- PostgreSQL;
- persistence/ORM approach;
- schema migration mechanism;
- repository/data-access pattern.

Implement persistence for the initial Phase 1 entities.

Use the existing local PostgreSQL development database where available.

Docker Compose may be introduced later where useful for reproducible
development or deployment, but is not required for the initial local
development environment.

## Required capabilities

The developer should be able to:

    start PostgreSQL
    initialise/migrate schema
    insert an opportunity
    retrieve an opportunity
    associate it with a source

Persistence configuration must use environment variables.

## Tests

Include:

- persistence integration tests;
- insert/read tests;
- relationship tests;
- migration verification.

## Deliberately excluded

Do not yet implement the complete final database schema.


# Phase 3 — Professional Profile

## Objective

Represent the user's professional evidence explicitly.

## Scope

Introduce concepts required for:

- ProfessionalProfile;
- ProfileDocument;
- ProfessionalService;
- Skill;
- Assignment;
- language capability;
- relevant countries/regions;
- organisations/clients where useful.

Seed the initial profile from the authoritative CV and Professional Services
documents.

The first implementation may use curated structured data rather than attempting
fully automated CV extraction.

## Important principle

The profile represents:

    "What can Jan credibly claim?"

It must remain distinct from:

    "What work does Jan currently want?"

## Provenance

Important structured profile information should retain enough provenance to
identify its authoritative source.

## Verification

The system can retrieve structured professional evidence suitable for later
matching against an opportunity.


# Phase 4 — Search Strategy and Preferences

## Objective

Represent the user's evolving opportunity-search strategy independently from
professional evidence.

## Accepted design

- `SearchStrategy` is the stable logical identity;
  `SearchStrategy.current_revision_id` points at the active revision.
- `SearchStrategyRevision` is an immutable snapshot; material changes create a
  new revision instead of mutating an active one.
- Revision content: `SearchTheme`, `StrategyCriterion`, `ExclusionCriterion`.
- `StrategyCriterion` replaces the earlier conceptual name `SearchCriterion` to
  avoid confusion with future acquisition/discovery search criteria.
- `StrategyCriterion` categories: `PREFERENCE` (ranking signal) and
  `HARD_CONSTRAINT` (deterministic eligibility input). Exclusions remain
  `ExclusionCriterion`.
- `PreferenceStrength` is ordinal (`STRONGLY_PREFERRED`, `PREFERRED`,
  `ACCEPTABLE`, `LESS_PREFERRED`); no numeric ranking weights in Phase 4.
- `StrategyParameterCode` plus structured, code-validated values; at most one
  row per `(revision, category, code)` for the MVP.
- No persistent FK from `SearchTheme` to `ProfessionalService`.
- Revision metadata: `revision_number`, `status` (`ACTIVE` / `SUPERSEDED`),
  `created_at`, `change_summary`, `change_source`, `supersedes_revision_id`,
  `content_hash`. `DRAFT`, `effective_from`, and `user_confirmed` deferred.
- Same semantic content (`content_hash`) → no new revision; changed content →
  new active revision.
- Phase 4 stores state only (filtering Phase 7, matching Phase 8, ranking
  Phase 9, conversation Phase 11). Later assessments should record the revision
  id used.

## Implementation sequence

### Phase 4A.1 — Search Strategy domain

Domain types, enums, validation per `StrategyParameterCode`, revision bundle,
unit tests.

### Phase 4A.2 — Persistence

PostgreSQL schema, mappers, repositories, integration tests.

### Phase 4A.3 — Revision activation / application service

Create revision, activate (supersede prior), load full revision; transactional
behaviour.

### Phase 4B — Curated initial Jan/JVB strategy

Human-reviewed curated JSON seed (dry-run / `--apply`, deterministic,
idempotent via `content_hash`).

## Required capabilities

The system must support:

- one current strategy;
- strategy revision history;
- configurable search themes and strategy criteria;
- ordinal preferences;
- active/inactive items within a revision;
- explicit exclusions.

Do not implement conversational modification, filtering, matching, or ranking in
Phase 4.

## Verification

A strategy can be created, persisted, retrieved, revised, and historically
inspected without changing `ProfessionalProfile`.


# Phase 5 — Opportunity Processing Foundation

## Objective

Build the source-independent processing pipeline before connecting many live
sources.

## Scope

Using fixtures or representative stored source data, implement:

    RawOpportunity
          |
          v
       Normalize
          |
          v
       Identify
          |
          v
      Deduplicate
          |
          v
    Change Detection
          |
          v
       Persist

Implement:

- normalized opportunity mapping;
- deterministic identity rules;
- duplicate handling;
- opportunity observations;
- lifecycle handling;
- basic change detection.

## Tests

Use representative fixtures.

Test:

- repeated ingestion of the same opportunity;
- duplicate source observations;
- changed deadline;
- changed description;
- new opportunity;
- unchanged opportunity.

## Verification

Repeated processing is idempotent and does not create unnecessary duplicate
opportunities.


# Phase 6 — First Real Source Connector

## Objective

Prove the acquisition architecture against one real opportunity source.

## Source selection criteria

The first source should:

- be relevant to the user's professional market;
- provide enough opportunities for realistic testing;
- be accessible reliably;
- preferably not require authentication;
- avoid browser automation if possible.

The exact first source should be selected immediately before this phase based
on current technical accessibility.

## Scope

Implement one source-specific connector.

The connector should:

- acquire source data;
- map it into RawOpportunity;
- preserve provenance;
- record scan results;
- handle expected failures;
- integrate with the Phase 5 pipeline.

## Verification

A real scan produces persisted normalized opportunities from one external
source.

Do not add multiple sources in this phase.


# Phase 7 — Filtering and Eligibility

## Objective

Reduce obviously unsuitable opportunities before expensive AI assessment.

## Scope

Implement deterministic filtering for criteria such as:

- expired deadlines;
- explicit national-only restrictions;
- explicit local-only restrictions;
- explicit nationality mismatch;
- internships;
- volunteer positions;
- explicitly junior positions;
- other unambiguous configured exclusions.

Filtering decisions must store reasons.

Manual override capability should be represented at domain/application level.

## Ambiguous cases

Do not force ambiguous text into deterministic rules.

Ambiguous cases should remain eligible for later AI interpretation.

## Verification

Known test cases produce predictable eligibility outcomes and explanations.


# Phase 8 — AI Relevance and Profile Matching

## Objective

Introduce the first AI reasoning capability.

## Scope

Select the initial AI provider/model and implement the AI abstraction defined
by the architecture.

Implement structured AI assessments for:

### Professional relevance

Determine whether the actual assignment aligns with the user's professional
scope and service areas.

### Profile matching

Assess how strongly the user's documented professional evidence supports the
opportunity requirements.

## Structured output

AI output must use validated structured schemas.

The assessment should capture relevant dimensions such as:

- service-area alignment;
- domain alignment;
- technical alignment;
- relevant assignment experience;
- seniority;
- international experience;
- donor/client experience;
- language fit;
- evidence;
- gaps;
- uncertainty;
- explanation.

## Context construction

Do not send the complete professional history indiscriminately.

Construct task-specific context from relevant professional evidence.

## Failure handling

An AI failure must not remove or invalidate the opportunity.

## Tests

Use mocked AI responses for routine tests.

Paid/live model calls should be limited to explicitly identified integration
tests or manual evaluation.

## Accepted design (Bootcamp MVP)

- One append-only `OpportunityProfileAssessment` per run (logical professional
  relevance + profile matching sections in one JSON result).
- `AssessmentModel` port with `FakeAssessmentModel` (tests) and
  `OpenAIAssessmentModel` (optional live use). Model via
  `JOBHUNTER_OPENAI_MODEL`; API key via `JOBHUNTER_OPENAI_API_KEY`.
- Ordinal relevance/alignment only; numeric scoring and ranking remain Phase 9.
- Deterministic `ProfileEvidenceContextBuilder` with configured caps; profile
  entity id allowlisting and opportunity excerpt validation.
- `input_digest` reuse skips repeat LLM calls when opportunity, strategy
  revision, profile evidence, schema, and model configuration are unchanged.
- Eligibility gating: auto-assess `ELIGIBLE`, `REVIEW_REQUIRED`, `UNKNOWN`;
  skip `INELIGIBLE` unless forced; skip `EXPIRED`/`CLOSED` unless forced.
- FAO list summaries: `source_data_sufficiency` = `LIST_SUMMARY_ONLY`; do not
  infer missing ToR requirements.
- Integrated after Phase 7 in FAO scan when OpenAI is configured.

## Acceptance criteria

- Persisted assessments with strategy revision id, digests, provider metadata,
  validation warnings, and structured JSON result.
- Normal pytest uses `FakeAssessmentModel` only; optional `live` marker for
  OpenAI.
- CLI `scripts/assess_opportunity_profile.py` supports opportunity id, source
  id, dry-run, force, and include-ineligible.
- AI failure does not invalidate opportunities or scan results.


# Phase 9 — Ranking and Explainability

## Objective

Prioritise eligible opportunities using professional fit and current search
strategy.

## Scope

Implement deterministic `ranking_v1` (no LLM). Combine Phase 8 structured
assessment with active `SearchStrategyRevision` (theme strengths, eligibility
context). Internal integer points for ordering; user-facing `HIGH` / `MEDIUM` /
`LOW` / `REVIEW` bands plus factors. Append-only `OpportunityRanking` persistence
with `input_digest` idempotency. CLI `scripts/rank_opportunities.py`. Production
ranking excludes `model_provider=fake` unless `--include-fake-assessments`.

## Required result

Each ranking explains main factors; rank order is computed dynamically (no
persisted `rank_sequence`).

## Verification

Changing SearchStrategy priorities can change ranking without modifying
ProfessionalProfile.


# Phase 10 — Minimal Dashboard

## Objective

Provide a usable interface for reviewing the first end-to-end results.

## Initial technology

Use Streamlit unless an architectural review before this phase identifies a
material reason to select another UI approach.

## Initial screens

Implement only the functionality required for useful review:

### Dashboard

Show summary information such as:

- latest scan;
- new opportunities;
- updated opportunities;
- high-priority opportunities;
- source failures.

### Opportunity List

Support:

- title;
- organisation;
- location;
- deadline;
- source;
- lifecycle;
- eligibility;
- relevance;
- ranking;
- basic filtering/sorting.

### Opportunity Detail

Show:

- normalized information;
- source URL;
- source provenance;
- AI assessment;
- matching evidence;
- gaps;
- ranking explanation.

## Principle

UI components call application services.

Do not place core filtering/ranking/business logic directly in Streamlit code.


# Phase 11 — Conversational Strategy Management

## Objective

Allow the user to evolve the search strategy through natural-language
conversation.

## Example

    User:
    "I'm getting too many general GIS positions. Focus more on LIS
    implementation and systems integration."

## Flow

Implement:

    Current Search Strategy
             +
        User Message
             |
             v
       AI Interpretation
             |
             v
    Proposed Structured Change
             |
             v
       User Review
             |
        confirm / reject
             |
             v
     SearchStrategyRevision

## Important rules

- conversation is not the authoritative state;
- persistent SearchStrategy is authoritative;
- material changes require confirmation;
- changes must be inspectable;
- previous strategy revisions must remain available;
- casual conversation must not silently alter ProfessionalProfile.

## Feedback integration

Opportunity feedback may be used to propose strategy changes.

Do not automatically learn substantial long-term preferences from isolated
feedback without confirmation.


# Phase 12 — Multi-Source Expansion

## Objective

Expand acquisition from the first source to the priority source catalogue.

## Approach

Add sources incrementally.

For each source:

1. investigate available acquisition methods;
2. prefer official API/feed;
3. evaluate structured endpoints;
4. use HTTP parsing where appropriate;
5. use browser automation only where required;
6. implement connector;
7. add representative fixtures/tests;
8. verify normalization;
9. verify duplicate handling.

## Candidate sources

Priority candidates include:

- World Bank eConsultant2;
- World Bank STEP;
- ADB CSRN;
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
- selected consulting firms;
- UNjobs;
- DevNetJobs.

Source priority and feasibility should determine actual implementation order.

## Source discovery

Introduce source-discovery support only after the configured source catalogue
is working reliably.


# Phase 13 — Scheduling and Notifications

## Objective

Allow JobHunter to operate without manual scan initiation.

## Scope

Implement scheduled execution of the scan pipeline.

Target schedule initially:

    Monday   08:00 Europe/Amsterdam
    Thursday 08:00 Europe/Amsterdam

Implement email reporting.

Reports should highlight:

- NEW high-priority opportunities;
- UPDATED relevant opportunities;
- STILL OPEN high-priority opportunities;
- source failures where useful.

### Phase 13 extension — HIGH opportunity alerts (completed)

Immediate SMTP/console alerts for **HIGH** production rankings only:

- integrated after Phase 9 ranking in `ScheduledPipelineOrchestrator`;
- append-only `opportunity_notifications` audit with unique `notification_key`
  per ranking row (`high_ranking:{ranking_id}`);
- activation limited to **new** ranking outcomes in the current worker run
  (`reused` false) — no automatic email for historical HIGH rows;
- failed sends recorded and retried; successful sends suppress duplicates;
- `notifications.high_ranking_alerts_enabled` in automation JSON;
- optional `JOBHUNTER_WEB_BASE_URL` for dashboard links in alert email.

Phase 8 assessment semantics and Phase 9 ranking semantics are unchanged.

## Important principle

Notifications use persisted scan results.

They must not independently repeat the discovery process.


# Phase 14 — Application Tracking

## Objective

Support the workflow after the user decides to pursue an opportunity.

## Scope

Implement:

- selection for action;
- application status;
- application date;
- remarks;
- follow-up;
- response history;
- application events.

Possible statuses include:

    considering
    selected
    preparing
    applied
    shortlisted
    interview
    rejected
    withdrawn
    awarded
    closed

The exact model should be reviewed before implementation.

## Verification

Application history remains separate from automated opportunity lifecycle
status.


# Phase 15 — CV and Cover-Letter Personalisation

## Objective

Generate grounded application materials for opportunities explicitly selected
by the user.

## Inputs

Use:

- selected opportunity;
- source description / Terms of Reference;
- ProfessionalProfile;
- authoritative CV;
- relevant assignments;
- Professional Services information.

## Outputs

Support:

- tailored CV;
- cover letter;
- expression of interest where appropriate.

## Grounding rule

The system may:

- select;
- reorganize;
- emphasize;
- summarize;
- accurately rephrase.

The system must not invent:

- assignments;
- qualifications;
- skills;
- technologies;
- languages;
- countries;
- clients;
- responsibilities;
- achievements.

## Human review

Generated documents are drafts until accepted by the user.

No automatic external application submission is included in this phase.


# Phase 16 — XLSX Export and Operational Features

## Objective

Add practical operational functionality around the core system.

## Scope

Implement XLSX export of opportunity information.

Candidate fields include:

- title;
- organisation;
- country;
- deadline;
- source;
- source URL;
- search theme;
- lifecycle;
- eligibility;
- relevance;
- profile match;
- ranking;
- application status;
- remarks.

Also review requirements for:

- source management;
- source health;
- strategy management;
- scan history;
- manual opportunity entry;
- URL validation.

Implement only features demonstrated to be useful.


# Phase 17 — Deployment

## Objective

Run JobHunter independently of the local development computer.

## Target architecture

Initial target:

    Internet
       |
       v
    HTTPS / Reverse Proxy
       |
       v
    Linux VPS
       |
       +-- JobHunter Web/UI
       |
       +-- JobHunter Worker
       |
       +-- PostgreSQL
       |
       +-- Persistent Documents

Use Docker / Docker Compose.

A small Hetzner Cloud VPS is a suitable initial deployment candidate, but the
application must not depend on Hetzner-specific services.

A possible production URL is:

    https://jobhunter.jvbgis.com

## Scope

Implement:

- production Docker configuration;
- persistent PostgreSQL storage;
- persistent document storage;
- HTTPS;
- production environment configuration;
- scheduled worker execution;
- restart behaviour;
- basic backup procedure;
- basic operational documentation.

## Deployment flow

Initially:

    Local development
          |
          v
        GitHub
          |
          v
    VPS deployment

CI/CD is optional and should be introduced only when useful.


# Phase 18 — Hardening and Further Evolution

## Objective

Improve reliability based on actual system usage.

Potential areas include:

- improved source monitoring;
- retry strategies;
- connector health reporting;
- better duplicate detection;
- richer change history;
- ranking calibration;
- strategy-learning proposals;
- improved profile retrieval;
- embeddings/pgvector if demonstrated useful;
- browser automation for difficult sources;
- improved document storage;
- authentication;
- automated backups;
- CI/CD;
- richer notifications;
- additional export formats.

Do not implement these merely because they appear on this list.

Each should be justified by observed requirements.


# 4. Cross-Phase Rules

## 4.1 Keep the Repository Working

Each implementation step should leave the repository in a working state.

Do not knowingly commit partially integrated functionality to the main working
branch unless explicitly agreed.


## 4.2 Tests Accompany Business Logic

Tests should be introduced with the functionality they protect rather than
being deferred until the end of the project.


## 4.3 Architecture Changes

If implementation reveals that `docs/architecture.md` should change:

1. stop before making a major architectural deviation;
2. explain the issue;
3. propose the change;
4. obtain acceptance where material;
5. update architecture;
6. continue implementation.


## 4.4 Database Evolution

Use migrations once persistent database schema implementation begins.

Do not manually modify production database structures outside the selected
migration mechanism.


## 4.5 AI Cost Awareness

Avoid unnecessary AI calls.

In particular:

- deterministic filtering should precede expensive AI assessment;
- unchanged opportunities should not automatically be reassessed;
- cached/persisted assessments should be reused where valid;
- tests should normally mock AI calls.


## 4.6 Source Robustness

One broken external source must not prevent processing of other sources.

Source-specific failures should be visible and diagnosable.


## 4.7 No Premature Browser Automation

Do not install or implement Playwright merely because it is part of the
candidate architecture.

Introduce it when a selected source demonstrably requires browser interaction.


## 4.8 No Premature Vector Architecture

Do not introduce embeddings, pgvector, or a vector database until profile
retrieval or opportunity similarity requirements demonstrate a need.


## 4.9 Human Control

Automated processing may:

- discover;
- filter;
- assess;
- rank;
- explain;
- draft.

The user retains control over:

- persistent material preference changes;
- pursuing an opportunity;
- overriding filters;
- final application documents;
- external application submission.


# 5. Initial Milestone

The first major milestone is a complete vertical slice:

    One real source
          |
          v
       Acquire
          |
          v
      Normalize
          |
          v
     PostgreSQL
          |
          v
       Filter
          |
          v
     AI Assessment
          |
          v
        Rank
          |
          v
       Dashboard

This milestone spans Phases 0–10.

It demonstrates the central JobHunter concept before significant effort is
spent adding source coverage, conversational strategy management,
personalisation, or production deployment.


# 6. Current Implementation Status

Phases 0–13 are complete for the Bootcamp MVP unattended-operation slice.

The current implementation step is:

    Phase 14 — Application Tracking

Phase 3 established the professional evidence foundation from the structured
project spreadsheet, Professional Services document, and CV.

The implemented professional evidence includes structured professional
services, assignments, capabilities, assignment-to-capability evidence,
skills, language capabilities, and country experience, with source
provenance where applicable.

Phase 4 introduced the separate persistent representation of what the user
currently wants from JobHunter, including an initial curated search strategy
seed.

This maintains the architectural distinction between:

    Professional Profile
    "What can Jan credibly claim?"

and:

    Search Strategy
    "What work does Jan currently want?"

Phase 5 implemented the source-independent processing pipeline (normalize,
identify/deduplicate, change detection, lifecycle, persist) with
`OpportunityObservation` and `OpportunityChange` persistence, deterministic
identity, and fixture-based tests.

Phase 6 implemented the first real connector (FAO Jobs) using the public
Taleo Career Section `searchjobs` JSON API, `SourceScan` persistence, and
integration with the Phase 5 `OpportunityProcessingService`.

Phase 12 added DevelopmentAid Jobs as the second connector
(`DevelopmentAidJobsConnector`, frontend JSON search/detail API), demonstrating
the same SourceScan → Phase 5 → Phase 7 → (optional Phase 8) path without
source-specific eligibility or dashboard logic.

Phase 13 added `ScheduledPipelineOrchestrator`, JSON automation configuration,
source scan adapters/registry, `automation_runs` audit persistence,
production-only batch assessment, optional Phase 9 ranking,
`NotificationSender` (console/SMTP) run summaries from persisted state, and
duplicate-safe immediate HIGH-band opportunity alerts (`opportunity_notifications`,
`HighRankingAlertService`).

**Deployment hardening (post–Phase 13):** Docker image, `docker-compose.yml`,
[deployment.md](deployment.md), SMTP notification adapter, test isolation for
developer `.env` OpenAI keys, and gitignored `config/automation.json`.

**Next functional phase:** Phase 14 — Application Tracking (not started).

Phase 7 implemented deterministic eligibility filtering via
`EligibilityFilterService`, persistent eligibility decisions and rule results,
and integration after Phase 5 processing (including FAO scans).

Phase 8 implemented AI profile/relevance assessment via
`OpportunityProfileAssessmentService`, persistent
`OpportunityProfileAssessment` records, deterministic evidence context
construction, grounded structured output validation, and integration after
Phase 7 (including FAO scans when OpenAI is configured).

Phase 9 implemented deterministic prioritisation via
`OpportunityRankingService`, `ranking_config_v1`, append-only
`OpportunityRanking` persistence, and `scripts/rank_opportunities.py`.

Accepted Phase 4 design decisions are recorded in Phase 4 above and in
`architecture.md` §7.5–7.6. Phase 5 processing boundaries and observation
semantics are recorded in `architecture.md` §12 and §14.
