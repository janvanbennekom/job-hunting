# [AGENTS.md](http://AGENTS.md)

## 1. Purpose

This repository contains the Job Hunting AI Agent, a personal AI-assisted
opportunity discovery and application-support system for Jan van
Bennekom-Minnema.

The system is not intended to be a generic job-search engine.

Its primary purpose is to discover international consulting assignments,
technical specialist roles, advisory assignments, implementation assignments,
and other professional opportunities that align with Jan's professional
profile, experience, capabilities, and preferred professional services.

The system should cast a sufficiently wide search net to avoid missing relevant
opportunities, then progressively filter, assess, and rank opportunities so
that attention can be focused on a relatively small number of strong matches.

The system should support, but not replace, the user's decision about whether
to pursue an opportunity.

## 2. User Professional Context

The primary user is a senior Geo-ICT and Land Administration Specialist with
more than 30 years of international experience.

Core professional domains include:

- land administration;
- cadastre and land registration;
- Land Information Systems (LIS);
- GIS and geospatial information systems;
- Spatial Data Infrastructures (SDI);
- geospatial software and database development;
- systems integration and interoperability;
- spatial data management and analytics;
- enterprise and solution architecture;
- land administration digital transformation;
- business process improvement;
- technical quality assurance;
- implementation support;
- capacity building and technology transfer.

The user values both implementation-oriented and advisory assignments, with
particular interest in hands-on technical delivery, implementation, technical
leadership, and assignments where substantial technical expertise is required.

The user's preferred professional service areas are:

1. Land Information System (LIS) Implementation
2. GIS & Geospatial Systems Implementation
3. Geospatial Software & Database Development
4. Geospatial Data Integration & Spatial Analytics
5. System Integration & Interoperability
6. Land Administration Digital Transformation
7. Technical Quality Assurance & Implementation Support
8. Business Process & Operational Improvement
9. Capacity Building & Technology Transfer

These interests and capabilities must be represented as configurable
professional-profile data rather than being hard-coded throughout the
application.

## 3. Core Functional Pipeline

The conceptual processing pipeline is:

```
Source Discovery / Source Connectors
                |
                v
       Opportunity Acquisition
                |
                v
         Normalisation
                |
                v
    Deduplication / Change Detection
                |
                v
      Eligibility Filtering
                |
                v
   Professional Relevance Assessment
                |
                v
       Profile Matching
                |
                v
   Ranking and Explanation
                |
                v
         Human Review
                |
         +------+------+
         |             |
         v             v
      Tracking    Personalisation
                       |
                +------+------+
                |             |
                v             v
          Tailored CV    Cover Letter
```

Individual components may use deterministic logic, AI reasoning, or a
combination of both.

Do not assume that every component is an autonomous AI agent.

## 4. AI vs Deterministic Logic

Use AI where semantic interpretation, contextual reasoning, or generation
provides material value.

Appropriate AI use cases include:

- interpreting job descriptions and Terms of Reference;
- understanding the actual nature of an assignment;
- semantic relevance assessment;
- matching opportunities against the professional profile;
- assessing evidence from previous assignments;
- identifying ambiguous eligibility requirements;
- explaining ranking decisions;
- discovering potentially relevant new sources;
- generating tailored CV content;
- generating cover letters or expressions of interest.

Prefer deterministic application logic where rules are explicit and
repeatability is important.

Examples include:

- deadline comparisons;
- explicit nationality requirements;
- explicit national/local consultant restrictions;
- junior/internship/volunteer exclusions;
- database persistence;
- CRUD operations;
- known identifier matching;
- application status transitions;
- scheduling;
- URL validation;
- export generation;
- configuration management.

Do not introduce an LLM call where conventional application logic is sufficient.

## 5. Opportunity Discovery

Opportunity discovery should favour recall over precision during the initial
search stage.

The discovery stage should cast a relatively wide net across configured
sources and search criteria.

Search criteria must be configurable and persisted. Do not hard-code search
terms into source connectors or business logic.

Search criteria should support:

- search themes;
- primary search terms;
- secondary search terms;
- combinations of terms;
- active/inactive status;
- priority;
- source-specific variations where necessary.

Relevant search themes include, but are not limited to:

- land administration;
- cadastre and cadastral systems;
- land registration;
- land information systems;
- land governance and land tenure;
- GIS and geospatial information;
- SDI and NSDI;
- digital registries and information systems;
- enterprise and solution architecture;
- interoperability and systems integration;
- digital transformation and digital government;
- spatial planning;
- agricultural land systems, LPIS and IACS.

The search model must allow themes and search criteria to evolve without
requiring application-code changes.

## 6. Source Management

Job and consultancy sources are first-class domain entities.

The system must support a configurable list of sources.

A source should be capable of storing information such as:

- name;
- organisation;
- URL or entry point;
- source type;
- priority;
- active/archive status;
- acquisition method;
- authentication requirement;
- last successful scan;
- last attempted scan;
- scan status;
- remarks.

Sources must be archived rather than physically deleted when historical
opportunities depend on them.

Source acquisition logic must be isolated from normalized opportunity
processing.

Each source connector should be responsible only for acquiring and mapping
source-specific information into a defined ingestion representation.

Do not allow source-specific HTML structures, API response structures, or
authentication logic to leak into core opportunity-processing logic.

Where the same opportunity appears on multiple sites, preserve all useful
source references while attempting to identify the authoritative/original
source.

## 7. Opportunity Provenance

Every opportunity must be traceable to its source.

Where available, preserve:

- source;
- source URL;
- original opportunity URL;
- source-specific identifier;
- retrieval timestamp;
- raw title;
- raw organisation/client;
- raw description or Terms of Reference;
- deadline as published;
- location as published;
- source metadata relevant to later verification.

Do not silently discard source information during normalization.

Derived AI assessments must remain distinguishable from source facts.

Never present AI-inferred information as though it were explicitly stated by
the source.

## 8. Normalized Opportunity Model

All source connectors must eventually map opportunities into a common
normalized domain representation.

The normalized model should be capable of representing at least:

- title;
- organisation/client;
- country/location;
- opportunity type;
- consultancy/employment classification;
- international/national/local classification where known;
- publication date;
- deadline;
- duration;
- expected start date where known;
- remote/on-site/hybrid information;
- required languages;
- required experience;
- required skills;
- description;
- Terms of Reference or equivalent;
- source references;
- search criteria that produced the hit;
- eligibility status;
- relevance assessment;
- profile-match assessment;
- ranking information;
- lifecycle status;
- application status;
- user remarks.

The exact implementation belongs in the architecture and domain model, not
in this instruction document.

## 9. Filtering and Eligibility

A keyword hit is not sufficient evidence that an opportunity is suitable.

Filtering must distinguish between:

1. explicit deterministic exclusions;
2. likely exclusions requiring interpretation;
3. professional relevance;
4. profile fit.

Examples of exclusion criteria include:

- deadline has passed;
- explicitly national consultant where international eligibility is not
possible;
- local consultant where residency or nationality is required;
- explicit nationality requirement that the user does not satisfy;
- junior positions;
- internships;
- volunteer assignments;
- mandatory language requirements the user cannot credibly satisfy;
- highly specialised roles outside the user's professional scope where a
matching keyword is incidental.

Filtering decisions should retain a reason.

Do not permanently discard rejected opportunities merely because they fail a
filter. Preserve enough information to audit and, where appropriate, manually
override the decision.

## 10. Professional Profile

The professional profile is a first-class domain concept.

Do not treat the CV merely as an unstructured prompt supplied repeatedly to an
LLM.

The system should support both:

1. authoritative source documents, such as the CV and Professional Services
  document; and
2. structured profile information derived from or maintained alongside those
  documents.

Structured profile information may include:

- professional positioning;
- service areas;
- domains;
- skills;
- technologies;
- standards;
- methodologies;
- sectors;
- organisations/clients;
- countries;
- languages;
- roles;
- years of experience;
- assignments;
- education;
- training;
- preferred assignment characteristics.

Maintain traceability between important profile claims and their evidence where
practical.

## 11. Evolving User Context and Search Strategy

The user's professional interests, availability, priorities, and preferred
types of assignments will change over time.

The system must therefore distinguish between relatively stable professional
evidence and evolving user preferences.

### Professional evidence

Professional evidence describes what the user can credibly claim and includes
information derived from authoritative sources such as:

- CV;
- Professional Services document;
- assignment history;
- education and training;
- documented skills and technologies;
- languages;
- countries and organisations worked with.

Professional evidence must not be changed merely because of conversational
preferences.

### Search strategy and preferences

Search strategy represents what the user currently wants the system to find
and prioritise.

This may include:

- preferred professional service areas;
- preferred assignment types;
- implementation vs advisory preference;
- desired technical focus;
- geographic preferences;
- travel constraints;
- assignment duration;
- remote/on-site preferences;
- client or donor preferences;
- emerging areas of interest;
- search themes;
- exclusions;
- ranking preferences.

These preferences must be persistent and changeable over time.

### Conversational updates

The user should be able to discuss changing professional interests and
job-search requirements with the system in natural language.

The system may interpret such conversations and propose changes to the
persistent search strategy.

For example:

```
User:
"I'm seeing too many generic GIS positions. Focus more strongly on
LIS implementation, system integration and Geo-ICT architecture,
while retaining senior international-development GIS implementation
assignments."
```

The system should translate this into explicit proposed configuration changes.

Material changes to persistent search strategy must be shown to the user
before being committed.

The user should not need to understand or manually edit the underlying
database structure to change the search strategy.

### Context layers

Keep the following concepts logically separate:

1. Professional Evidence
  What the user can credibly claim.
2. Current Search Strategy
  What opportunities the user currently wants to find.
3. Conversation
  Natural-language interaction through which the user can explore,
   explain, and modify the current strategy.
4. Search History and Feedback
  Evidence from previous scans and explicit user decisions that may help
   improve future searches.

Do not silently convert casual conversation into permanent professional
evidence or search preferences.

### Feedback and adaptation

The system should support explicit feedback on opportunities, for example:

- relevant;
- not relevant;
- too advisory;
- too managerial;
- too junior;
- too GIS-generic;
- too remote-sensing focused;
- strong match;
- interesting despite low score;
- similar opportunities wanted;
- do not show similar opportunities.

Such feedback may be used to propose improvements to search, filtering, and
ranking behaviour.

Do not automatically make substantial long-term changes based on a single
user action unless that behaviour has explicitly been enabled.

Changes to search strategy should remain inspectable and reversible.

## 12. Profile Matching

Profile matching must be evidence-based.

A high score must not result merely from keyword overlap.

The assessment should consider dimensions such as:

- professional-service alignment;
- domain alignment;
- technical alignment;
- relevant assignment experience;
- role/seniority alignment;
- international experience;
- client/donor experience;
- country or regional experience where relevant;
- language requirements;
- implementation vs advisory orientation;
- eligibility;
- other configurable preferences.

When an AI model produces a match assessment, it should return structured
results rather than only free-form prose.

Where practical, assessments should include:

- dimension;
- score or assessment;
- supporting evidence;
- gaps;
- uncertainty;
- explanation.

Do not invent experience or qualifications not supported by the professional
profile.

## 13. Ranking

Ranking should help prioritize human attention.

The ranking model must be configurable and explainable.

Do not hide ranking logic inside a single opaque prompt.

The system should be capable of combining deterministic information and AI
assessment.

Ranking weights must be configurable rather than embedded throughout source
code.

A ranking should retain sufficient information to explain why an opportunity
received its result.

Do not automatically apply for an opportunity based solely on its ranking.

## 14. Opportunity Lifecycle

The system must distinguish newly discovered opportunities from opportunities
already known from previous scans.

Important lifecycle states include:

- NEW;
- UPDATED;
- STILL OPEN;
- CLOSED or EXPIRED where applicable.

The system should also be capable of identifying opportunities that remain
particularly relevant across repeated scans.

Change detection should identify material changes such as:

- deadline;
- title;
- Terms of Reference;
- eligibility;
- location;
- duration;
- status;
- source content.

Do not create a duplicate opportunity simply because the same opportunity was
retrieved during another scan.

## 15. Human Control

The system is decision support.

The user retains control over:

- whether an opportunity is relevant;
- whether a filter decision should be overridden;
- whether an opportunity should be pursued;
- application status;
- remarks;
- final CV;
- final cover letter;
- submission of an application.

Manual user decisions must not be overwritten silently by later automated
processing.

## 16. Application Tracking

The system should support tracking opportunities after human selection.

Application-related information may include:

- selected for action;
- application status;
- application date;
- response history;
- follow-up dates;
- remarks;
- documents generated;
- documents submitted.

Application history should preserve meaningful changes over time.

## 17. Personalisation

CV and cover-letter personalisation occurs only after the user decides that an
opportunity should be pursued.

Generated documents must remain grounded in the authoritative professional
profile and source CV.

Never fabricate:

- qualifications;
- employment;
- assignments;
- technologies;
- responsibilities;
- languages;
- countries of experience;
- clients;
- achievements.

Tailoring means selecting, emphasizing, reorganizing, and accurately describing
relevant experience.

It does not mean inventing experience to improve apparent fit.

## 18. Persistence

Information that must survive application restarts or repeated scans should use
persistent storage.

Do not rely on in-memory state for domain information that must persist.

Persistent concepts are expected to include, among others:

- sources;
- search criteria;
- exclusions;
- professional profile;
- source documents;
- current search strategy;
- search strategy history;
- user feedback;
- opportunities;
- opportunity-source relationships;
- scan runs;
- hits;
- assessments;
- rankings;
- application tracking;
- user remarks.

The selected persistence technology is an architectural decision and must not
be assumed solely from this document.

## 19. Security and Credentials

Never commit credentials, passwords, API keys, tokens, cookies, connection
strings containing secrets, or other sensitive authentication material to the
repository.

Use environment variables or an approved secrets mechanism.

Provide `.env.example` where environment configuration is required.

`.env` and equivalent secret files must be excluded from version control.

Site credentials must not be stored in plaintext application data.

Never log secrets.

Browser automation must not bypass security controls or access restrictions
that the user is not authorised to access.

## 20. External Websites

Treat external job sites as independent systems whose interfaces may change.

Prefer, in order where appropriate:

1. documented APIs or feeds;
2. stable public structured endpoints;
3. conventional HTTP retrieval and parsing;
4. browser automation when interaction or client-side rendering requires it.

Do not introduce browser automation merely because it is possible.

Keep acquisition strategies replaceable.

Respect authentication requirements, technical restrictions, and applicable
site conditions.

## 21. Engineering Principles

Apply the following principles:

### Simplicity

Implement the simplest solution that satisfies the current requirement.

Avoid speculative infrastructure and abstractions.

### Separation of concerns

Keep acquisition, normalization, filtering, matching, ranking, persistence,
presentation, and document generation logically separated.

### Modularity

Source-specific implementations must be replaceable without redesigning the
core application.

AI providers and models should not unnecessarily leak into domain logic.

### Configuration over hard-coding

Search criteria, source definitions, exclusion criteria, ranking weights, and
similar user-maintained information should be configurable.

### Explainability

Important automated decisions must be inspectable.

### Provenance

Preserve where information came from and distinguish source facts from derived
information.

### Idempotency

Repeated processing of the same source data should not unnecessarily create
duplicate records or inconsistent state.

### Reproducibility

Important deterministic transformations should produce consistent results for
the same inputs.

### Auditability

Important automated and manual changes should be traceable where practical.

### Maintainability

Prefer clear code and explicit domain models over clever or unnecessarily
abstract implementations.

## 22. Coding Guidelines

Follow the language and framework conventions selected in architecture.md.

General rules:

- use meaningful names;
- keep functions and classes focused;
- use type information where supported;
- avoid unexplained magic values;
- centralize configuration;
- handle expected failures explicitly;
- avoid broad exception swallowing;
- log useful operational context;
- keep domain logic independent from presentation code;
- keep external integrations behind defined interfaces;
- avoid premature optimization;
- avoid unnecessary dependencies;
- document non-obvious design decisions.

Do not refactor unrelated code while implementing a bounded task unless the
refactor is necessary and explained.

## 23. Testing

Important business rules require automated tests.

Prioritize tests for:

- normalization;
- deterministic exclusions;
- deadline handling;
- deduplication;
- change detection;
- lifecycle transitions;
- ranking calculations;
- manual overrides;
- source mapping;
- persistence behaviour.

AI behaviour should be tested at defined interfaces and structured-output
boundaries rather than relying solely on exact natural-language output.

External source tests should not unnecessarily depend on live websites.

Use fixtures or stored representative responses where appropriate.

## 24. Observability

Scheduled and automated processing must provide enough information to diagnose
failures.

Relevant events include:

- scan started;
- scan completed;
- source scan failed;
- number of records retrieved;
- number of new opportunities;
- number of updated opportunities;
- number excluded;
- AI assessment failure;
- notification failure.

Logging must not expose credentials or other secrets.

## 25. Repository Documentation

The repository uses the following core documents:

### [AGENTS.md](http://AGENTS.md)

Defines standing instructions and engineering principles for AI coding agents.

### [architecture.md](http://architecture.md)

Defines the current system architecture, technology decisions, domain
boundaries, important interfaces, and architectural decisions.

### [implementation-plan.md](http://implementation-plan.md)

Defines implementation phases, current progress, and the sequence of work.

Agents must read these documents before making significant changes.

## 26. Architectural Discipline

Do not silently change the architecture.

When implementation reveals that an architectural decision should change:

1. identify the issue;
2. explain why the current architecture is insufficient;
3. propose the smallest appropriate change;
4. update architecture.md when the change is accepted;
5. then implement against the revised architecture.

Do not introduce major frameworks, databases, AI orchestration systems,
deployment platforms, or external services without an explicit architectural
reason.

## 27. Incremental Development

Development is intentionally incremental.

When given a bounded implementation task:

- implement only the requested scope;
- do not automatically implement later phases;
- do not add speculative functionality;
- identify dependencies or blockers;
- run relevant tests;
- report what changed;
- report tests performed;
- report unresolved issues;
- suggest, but do not automatically execute, logical next steps.

A successful implementation should leave the repository in a working state.

## 28. Working With Existing Code

Before modifying existing functionality:

1. inspect the relevant code;
2. understand the current behaviour;
3. inspect existing tests;
4. identify affected interfaces;
5. make the smallest coherent change.

Do not replace working implementations solely because another approach appears
more fashionable or elegant.

## 29. Definition of Done

A bounded implementation task is complete when:

- requested functionality is implemented;
- architecture remains consistent;
- relevant tests exist and pass;
- existing tests continue to pass;
- errors are handled appropriately;
- configuration is not unnecessarily hard-coded;
- no secrets are committed;
- relevant documentation is updated;
- the implementation does not silently include unrelated future work.

## 30. Phase-by-Phase Implementation Autonomy

The project is implemented phase by phase.

For an approved phase, the implementation agent should normally complete
the full phase without requesting approval for intermediate implementation
steps.

The agent may autonomously decide:

- module and file organization consistent with the architecture;
- implementation details;
- repository and mapper structure;
- database indexes and routine constraints;
- test organization;
- minor refactoring;
- non-destructive migration mechanics;
- minor corrections required to complete the accepted phase.

The agent must stop and request review when implementation would require:

- changing an accepted architectural decision;
- changing the meaning of an existing domain concept;
- introducing a significant new domain concept;
- making a destructive or risky data migration;
- introducing a major new dependency or technology;
- resolving a material business-rule ambiguity;
- expanding scope into a later phase;
- weakening provenance, auditability, revision history, or security.

Within a phase the normal workflow is:

1. inspect existing implementation and governing documentation;
2. determine the detailed implementation design;
3. implement the complete phase;
4. run unit and integration tests;
5. apply and verify migrations where applicable;
6. verify existing functionality remains intact;
7. update documentation where the completed implementation requires it;
8. review Git scope;
9. commit the completed phase;
10. provide a concise completion report.

Intermediate approval is not required unless one of the stop conditions
above is encountered.

## 31. Agent Response After Implementation

After completing a Cursor implementation task, report:

### Implemented

A concise description of what changed.

### Files changed

List created, modified, or deleted files.

### Tests

List tests executed and their results.

### Decisions

Identify implementation decisions that are not obvious.

### Issues

List unresolved problems, assumptions, or limitations.

### Architecture impact

State whether architecture.md needs modification.

### Suggested next step

Suggest the smallest logical next implementation step.

Do not automatically implement the suggested next step unless explicitly asked.