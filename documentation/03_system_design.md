# Phase 3 System design

Cricbuzz LiveStats will be a modular Python application with a Streamlit interface, application services, a provider adapter and SQL repositories. These components initially run in one application process. Separate responsibilities make the project easier to learn, test and maintain without introducing a separate web server or distributed infrastructure.

This document completes the architecture phase. It defines responsibilities and data flows; it does not implement the application, select an API subscription, create tables or solve the 25 SQL questions.

## 1 Architecture decisions

| Decision | Proposed design | Reason and boundary |
| --- | --- | --- |
| Application shape | Modular monolith | One runnable application, with explicit internal module boundaries |
| Entry point | main.py | Matches the assignment deliverable and assembles navigation and dependencies |
| Frontend | Streamlit pages | Python interface for scores, stats, SQL and CRUD |
| Backend | Python services inside the application | Coordinates business operations; a separate REST backend is unnecessary initially |
| HTTP integration | requests through a Cricbuzz provider adapter | Keeps provider JSON and authentication out of page code |
| Initial database | SQLite for local learning | Low setup effort; hosted persistence and multi-user writes need review before deployment |
| Database access | SQLAlchemy connection management plus repositories | Central connection setup with explicit transaction boundaries |
| Other engines | PostgreSQL and MySQL adapters/configuration | Preserve portability; verify each engine before claiming support |
| Analytics | Saved SQL with engine-specific variants where necessary | Keeps the 25 questions inspectable and teaches SQL directly |
| Refresh | Explicit refresh with a configurable minimum interval | Controls request volume; interval depends on verified provider quotas |
| Sample mode | Explicit, separate sample dataset | Supports learning without credentials and cannot masquerade as live data |
| Access | Local trusted operator initially | Public CRUD and custom SQL require the additional controls below |

These are architectural choices for the planned implementation. Provider field coverage and database design can require documented revisions in Phases 4–5.

## 2 Text architecture diagram

```text
                         USER'S BROWSER
                               |
                               v
+------------------------------------------------------------------+
| STREAMLIT FRONTEND                                               |
| Home | Live Matches | Top Players | Analytics | CRUD | Settings    |
| Forms, filters, tables, charts, source labels and error messages   |
+-------------------------------+----------------------------------+
                                | validated operation request
                                v
+------------------------------------------------------------------+
| APPLICATION SERVICES                                             |
| MatchService | PlayerStatsService | IngestionService               |
| PlayerService | MatchStatsService | AnalyticsService               |
| Validation, access checks, orchestration, transaction decisions    |
+----------+--------------------------+-----------------------------+
           |                          |
           v                          v
+-------------------------+   +------------------------------------+
| API LAYER               |   | ANALYTICS LAYER                    |
| CricbuzzClient          |   | Saved query registry Q01 ... Q25   |
| ProviderAdapter         |   | Parameters, dialect selection,     |
| Timeouts, retry, parsing|   | read-only custom query execution   |
+------------+------------+   +----------------+-------------------+
             |                                 |
             v                                 v
    SELECTED CRICBUZZ API           +------------------------------+
    (external provider)             | REPOSITORIES / DATA ACCESS   |
                                    | Parameterized reads/writes   |
 API response -> adapter ->         | Transaction-scoped sessions  |
 ingestion service -> repositories  +--------------+---------------+
                                                   |
                                                   v
                                    +------------------------------+
                                    | utils/db_connection.py       |
                                    | Reader/writer connection     |
                                    | factories and engine setup   |
                                    +--------------+---------------+
                                                   |
                                                   v
                                    +------------------------------+
                                    | RELATIONAL DATABASE          |
                                    | SQLite initially             |
                                    | PostgreSQL/MySQL alternatives|
                                    +------------------------------+

CROSS-CUTTING SUPPORT
  config.py       -> validated configuration injected at startup
  models/         -> normalized record and operation contracts
  utils/          -> dates, cricket-unit conversions, safe logging
  access policy   -> service checks for writes and custom SQL
  cache policy    -> result reuse, freshness and invalidation
```

Arrows show calls. Records and results return through the same boundaries. A page calls a service; it does not issue provider requests or open its own database connection. An adapter translates provider records but does not commit database transactions.

## 3 Frontend layer

The frontend collects input and presents results. Page functions should remain small enough to explain independently during Phase 12.

| Page | Inputs | Service calls | Outputs |
| --- | --- | --- | --- |
| Home | Navigation choice | Optional dataset summary | Project purpose, instructions, documentation and folder guide |
| Live Matches | Match selection and refresh | MatchService list/detail refresh | Match cards, scorecard, batting/bowling details, venue, status, refresh time |
| Top Players | Format and category | PlayerStatsService leaders | API-backed leader table and chart, source and snapshot date |
| Analytics | Question, parameters, analysis date; custom SQL for authorized operator | AnalyticsService | SQL text, results, coverage warnings and controlled execution errors |
| CRUD | Entity type, selected record, create/edit/delete form | PlayerService or MatchStatsService | Current records, validation feedback and committed-change confirmation |
| Settings | Permitted operational preferences | Configuration/status service | Data mode, connection health, refresh policy and masked credential status |

Settings never displays raw API keys or database URLs containing passwords. Secrets are supplied outside the interface initially. A successful read is not labeled a successful live fetch unless a provider request actually succeeded.

Frontend session state holds interaction choices and form context. It is not the persistent database or an authorization authority. Required fields and obvious invalid input can be checked in forms, but services must repeat authoritative validation because future callers may bypass the UI.

## 4 Backend and service layer

A service represents an application operation, such as refreshing a match or correcting a batting record. It checks rules and delegates work to narrower components.

| Component | Owns | Does not own |
| --- | --- | --- |
| MatchService | Match listing, details, refresh orchestration and snapshot selection | Raw HTTP headers or chart rendering |
| PlayerStatsService | Format/category selection and career-stat snapshot selection | Reconstructing career totals from incomplete history without disclosure |
| IngestionService | Identity resolution, import validation, write ordering and import outcome | Provider-specific JSON traversal |
| PlayerService | Player CRUD, validation and dependent-record policy | HTTP fetching |
| MatchStatsService | Batting/bowling/fielding record CRUD, match/innings/player consistency | Whole-match deletion unless later explicitly designed |
| AnalyticsService | Saved-query selection, validated parameters, coverage metadata and execution limits | Changing stored records |

Service dependencies are supplied during application setup. Tests can substitute a fixture API client or temporary database without changing business rules. Use classes for stateful clients and services where they clarify dependencies; keep pure calculations as ordinary functions.

## 5 Database and repository layer

Repositories contain persistence operations such as finding a player, upserting a match snapshot and reading eligible analytical records. Central connection factories live in utils/db_connection.py as required by the brief.

The service defines the logical unit of work. A repository receives a transaction-scoped connection and does not independently commit halfway through a service operation. Failed validation or database errors trigger rollback. Keep network requests outside write transactions to avoid holding database locks while waiting on the provider.

Conceptual data groups, pending the Phase 4 schema:

- Reference records: countries, teams, players, venues and formats.
- Competition records: series, matches, participating teams and toss/results.
- Participation and performance records: playing XI where available, innings, batting, bowling and fielding.
- Career statistics: provider totals by player and format, including source and snapshot time.
- Import provenance: provider identity, fetch time, record source and completeness information.

Reference integrity belongs in database constraints as well as application validation. Provider identity uniqueness supports repeatable imports. Indexes and deletion behavior will be specified with the schema, not guessed here.

### Portability boundary

Choose the engine through configuration. Keep connection setup, foreign-key enforcement, upsert behavior and query dialect selection behind data-access boundaries. Date arithmetic, quarterly grouping and standard deviation may need separate SQL variants or verified engine-specific functions.

| Engine | Architecture target | Current verification |
| --- | --- | --- |
| SQLite | Local baseline | Not implemented or tested |
| PostgreSQL | Alternative persistent deployment engine | Not implemented or tested |
| MySQL | Alternative supported engine design | Not implemented or tested |

Changing a connection URL alone is not proof of portability. Maintain equivalent-result fixtures for each engine when compatibility is implemented.

## 6 API layer

CricbuzzClient owns the HTTP session, configured provider base URL, authentication, explicit timeouts, bounded retries and request errors. ProviderAdapter transforms external JSON into normalized records. The selected provider contract, paths, quotas and supported pagination remain pending Phase 5.

A normalized response should carry records plus source, fetched-at time, upstream update time if available, and completeness. Missing fields remain unknown instead of becoming zero. Do not create a player identity from a display name alone when a reliable provider ID exists.

Retry eligible transient failures only within a bounded attempt/time budget. Authentication errors should prompt configuration review. Rate-limit failures should preserve the last successful snapshot and respect provider retry guidance rather than hammering the endpoint. Never log credential headers or a credential-bearing URL.

## 7 Analytics layer

The saved-query registry will contain a stable question ID, description, supported parameters, required data fields, SQL variant by engine and expected output columns. Phase 11 creates each actual solution only after the preceding lesson is accepted with NEXT.

Analytics executes against stored, identified datasets. It reports scope and relevant missing coverage, especially when a query requires career totals, ten performances, repeated venue appearances or multiple years of data. A zero-row result is distinct from a query error or unavailable fields.

Custom SQL runs through a dedicated execution path with database-enforced read-only access, one permitted query, bounded result retrieval and an execution-time budget. Prefix checks such as “starts with SELECT” are insufficient. SQLite requires a restricted read connection and execution controls; server engines require restricted reader credentials and appropriate statement limits. Exact controls will be implemented and tested for the selected engine before exposing this feature. Disable custom SQL to public visitors by default.

Charts consume query results; they do not silently reimplement the SQL logic in a different way. Ratios must preserve their denominators. Run and wicket margins remain distinct. Consecutive-position combined-score questions remain labeled as the assignment's proxy.

## 8 Utility and configuration layers

Utilities provide small, reusable operations: overs-to-legal-balls conversion, UTC timestamp parsing, display-time conversion, safe logging and consistent exception formatting. Domain validation belongs in models/services rather than an oversized generic utility file.

Configuration is loaded and validated once during startup, then supplied to clients and connection factories. Proposed settings include:

| Setting | Purpose |
| --- | --- |
| DATA_MODE | Explicit live or sample dataset selection |
| DATABASE_URL | Main database connection; treated as a secret if it contains credentials |
| READ_DATABASE_URL | Restricted query connection where separate credentials are needed |
| CRICBUZZ_API_BASE_URL / API_KEY | Provider connection, verified in Phase 5 |
| HTTP_CONNECT_TIMEOUT / HTTP_READ_TIMEOUT | Bounded network waiting |
| API_MAX_ATTEMPTS | Bounded retry policy |
| REFRESH_MIN_SECONDS / CACHE_TTL_SECONDS | Quota-aware refresh and reuse policy |
| QUERY_ROW_LIMIT / QUERY_TIMEOUT_SECONDS | Bounded analytics execution |
| DISPLAY_TIMEZONE | Human-readable local timestamps; initially Asia/Kolkata |
| APP_ACCESS_MODE | Local operator or public read-only mode |

Names are proposed contracts, not implemented environment variables. Keep real values in environment variables or deployment secrets; commit placeholder examples only. Never accept an arbitrary provider URL from an untrusted visitor. Missing live credentials should produce a clear configuration state, not an undisclosed switch to fake live data.

## 9 Authentication and authorization

Authentication asks who is using the app. Authorization decides which operations that person may perform. They are separate from the provider API key, which identifies the app to the data provider.

For the initial local learning application, a trusted operator can use CRUD and custom SQL without implementing an account system. This assumes access is limited to the operator's machine. The default public deployment policy is read-only browsing, with writes, configuration changes and arbitrary SQL disabled.

If public administrative access is later selected, introduce a verified identity provider or hosting authentication and enforce permissions at service entry points. Hiding a sidebar item or setting a session-state boolean is not access control. Reader and writer database privileges remain separate. Authentication implementation becomes a prerequisite for that deployment, not an extra requirement for the local prototype.

## 10 Data flows

### A Live match refresh

1. The user requests a match list or selected scorecard; the page calls MatchService.
2. The service checks data mode, requested scope, freshness and minimum refresh interval.
3. A reusable snapshot can be returned with its original timestamp. A new permitted refresh calls CricbuzzClient outside a database transaction.
4. The adapter parses the response, validates identifiers and distinguishes a partial snapshot from a complete one.
5. IngestionService validates normalized records and opens one transaction for the chosen import unit, initially one match snapshot.
6. Repositories upsert related records in dependency order. On failure, the unit rolls back and the previous successful snapshot remains available.
7. On commit, the data revision changes, dependent cached results are invalidated, and the page receives the stored result with source and freshness metadata.
8. On provider failure, show the last successful snapshot as stale or show a clear unavailable state if no snapshot exists.

A partial scorecard must not erase previously stored detail merely because a field is absent in a response. Source/version timestamps should prevent older snapshots overwriting newer ones when requests complete out of order. The exact merge rules depend on the provider contract.

### B Top player statistics

1. The page sends format and category to PlayerStatsService.
2. The service selects a fresh API aggregate snapshot or requests the supported provider capability.
3. The adapter maps the result to career-stat records with source and snapshot date.
4. The ingestion transaction persists validated records; the service returns leaders for a table/chart.
5. If only imported match history is available, label a separately computed ranking as dataset totals rather than provider career totals.

### C Saved SQL analysis

1. The user chooses a question, allowed filters and an analysis date.
2. AnalyticsService validates parameters and checks known data coverage.
3. The registry selects the SQL variant for the configured database engine.
4. A read connection executes parameterized SQL within output/time limits.
5. The page displays results, scope and any eligibility warning. No rows is a normal outcome.

### D CRUD transaction

1. An authorized operator selects a player or match-stat record and submits a form.
2. The service validates fields, identity, relationships and current record version.
3. A transaction creates, updates or deletes the requested record under the schema's dependency policy.
4. Missing records, conflicting edits and invalid dependencies produce a controlled error and rollback.
5. Commit advances the dataset revision. The interface reloads affected records and analytics after invalidation.

API-sourced records and manual edits need an explicit ownership policy. Proposed rule: provider refresh owns provider records; operator overrides are explicit and preserved separately, or API-owned fields are read-only. Phase 4 will select a concrete representation so a refresh never silently overwrites a promised persistent correction.

### E Custom SQL

1. An authorized local operator submits SQL on the Analytics page.
2. The service applies the allowed-statement policy and invokes the restricted reader executor.
3. The database permission boundary denies writes; execution and result limits bound resource use.
4. The UI receives a bounded table or a sanitized error. It does not receive a writer connection.

## 11 Caching, consistency and failures

Cache result data by operation, filters, data mode, source scope and dataset revision. Public result caches must not hold user-specific permissions or secrets. Cache reusable engine/client resources separately from result tables; acquire a fresh transaction scope for each operation rather than sharing an open transaction across users.

Preserve the original fetched-at timestamp on cache hits. Advance the revision only after successful writes, and do not show a committed-success message before commit. Start with one application instance; multiple instances require a shared revision/invalidation mechanism and coordinated ingestion before scaling.

| Failure | Required behavior |
| --- | --- |
| No live matches | Display a normal empty state |
| Missing API configuration | Explain setup requirement; sample mode remains an explicit choice |
| Timeout or transient upstream failure | Bound retries and display stale data with its timestamp if available |
| Invalid JSON or unrecognized structure | Reject the affected import unit; log sanitized diagnostic context |
| Constraint or validation error | Roll back writes and show actionable field/context feedback |
| Concurrent edit | Reject a stale update using a version check; invite reload |
| Database unavailable | Explain that reads/writes are unavailable without reporting success |
| Query timeout or excess output | Cancel/stop within the configured execution policy and explain the limit |
| Partial historical coverage | Identify limitations without fabricating qualifying records |

Log operation name, safe entity identifiers, outcome, duration and a correlation identifier. Avoid entire response dumps or sensitive configuration. Logs support debugging; the optional full CRUD audit trail remains a separate enhancement.

## 12 Deployment and verification boundaries

Local execution consists of the Streamlit app, a SQLite file outside source-controlled sample inputs, and outbound provider requests. Sample and live databases should use separate connection targets so synthetic rows cannot appear in live analytics.

For hosted operation, decide persistent storage and backups before relying on local files. An external PostgreSQL/MySQL service is an architectural option; no cloud account or paid resource is provisioned in this phase. Configuration supplies runtime secrets. A background ingestion scheduler is a later improvement, not part of the initial request-driven refresh flow.

Planned verification targets, not tests already run:

- Adapter tests with sanitized fixtures, missing fields and malformed payloads.
- Import tests proving duplicate snapshots do not duplicate data and failures roll back.
- Repository tests for foreign keys, deletion policy, version checks and manual overrides.
- SQL fixtures with known results and boundary cases for the 25 questions.
- Reader-executor checks proving writes are denied and limits are enforced.
- UI checks for navigation, forms, live/sample labels and stale/empty/error states.
- Engine compatibility checks for each database before it is marked supported.

## 13 Requirement traceability

| Phase 2 requirements | Architecture response |
| --- | --- |
| API-01–07 | Client, adapter, ingestion transaction, provenance and freshness policy |
| DB-01–09 | Repositories, central connection factory, relational groups and dialect boundary |
| UI-01–08 | Six page contracts, services, cache invalidation and restricted SQL path |
| CRUD-01–06 | Player/MatchStats services, validation, transaction, dependency and edit-conflict rules |
| Q01–Q25 | Saved-query registry, historical coverage and engine-specific SQL strategy |
| DEL-01–05 | main.py composition, modular boundaries, secrets and error contracts |
| DEL-06–10 | Versioning, setup, demo, recording and timeline remain delivery tasks |
| LEARN-03 | All requested layers, authentication assessment, text diagram and data flows in this guide |

## Phase completion

**What we completed:** selected a modular application architecture; defined frontend, backend, database, API, analytics, utility and configuration boundaries; assessed access control; documented five data flows, cache behavior, failure handling and deployment constraints.

**Files created:** documentation/03_system_design.md. The Phase 2 checklist is updated to record architecture completion; database design and all implementation features remain pending.

**Concepts learned:** modular monolith, dependency injection, adapters, repositories, transaction ownership, authentication versus authorization, read/write separation, idempotent ingestion, provenance and cache invalidation.

**Common mistakes to avoid:** HTTP requests in page functions, network calls inside write transactions, treating hidden controls as permissions, assuming every SQL engine behaves identically, mixing sample and live data, and overwriting manual edits during refresh.

**Next phase preview:** Phase 4 converts these conceptual data groups into normalized entities, an ER diagram, primary and foreign keys, indexes, constraints, deletion rules and SQL CREATE TABLE statements. It will also resolve the record-ownership representation. Provider coverage stays subject to Phase 5 verification.

Phase 4 awaits your confirmation as required by the adopted mentoring prompt. No application code, schema or SQL-question solutions have been generated in this phase.
