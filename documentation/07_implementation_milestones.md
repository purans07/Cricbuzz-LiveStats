# Phase 7 Implementation milestones

This plan turns the requirements and architecture into eight implementation milestones. Each milestone defines objectives, files, concepts and observable completion evidence. Completing this plan does not mark any implementation milestone complete.

The current repository contains the folder scaffold and validated design DDL. It has no working application services, installed project environment, persistent database or verified live API integration. No provider/version has been selected. These statuses remain unchanged by this document.

## How milestones relate to learning phases

A milestone groups implementation outcomes; a phase groups lessons. The numbering is intentionally different: milestone 2 is database implementation, while learning Phase 2 was requirements analysis.

| Milestone | Main learning phases | Dependency | Current status |
| --- | --- | --- | --- |
| M1 Environment setup | Setup at the start of Phase 8 | Existing scaffold | Pending |
| M2 Database | Phase 8 | M1 | Pending; design DDL already available |
| M3 API | Phase 9 | M2 and verified provider contract | Complete; authenticated acceptance and coverage limits in 09_api_implementation.md |
| M4 CRUD | Phase 10 | M2; follows Phase 9 in the learning sequence | Complete at service layer; 10_crud_guide.md |
| M5 Analytics | Phase 11 | M2 and suitable data; follows Phase 10 | Pending, 0 of 25 queries |
| M6 Dashboard | Phases 12–14 | Service contracts from M3–M5 | Pending |
| M7 Testing | Checks throughout; consolidated in Phase 15 | Implemented functionality | Pending |
| M8 Deployment | Phase 16 | M7 and a selected deployment target | Pending |

Phases 17 and 18 then finish submission documentation, recording preparation and 50 interview questions with answers. Error handling and meaningful checks accompany implementation; Phases 14 and 15 review their coverage rather than postponing quality work until the end.

## M1 Environment setup

**Objectives**

- Establish a project-local Python environment and record the actual runtime version.
- Replace commented dependency proposals with a tested installation set. Runtime candidates are Streamlit, requests, pandas, SQLAlchemy and Plotly; pytest supports verification. Add database drivers only for engines actually being configured.
- Implement a small validated configuration contract for sample mode and the local database, extending it when API/UI work needs additional settings.
- Establish local Git tracking with secret/runtime exclusions checked before staging. Remote repository creation or publication is not required for this milestone.

**Files to implement or update:** requirements.txt, requirements-dev.txt, config.py, .env.example, .gitignore and README.md. Proposed new guide: documentation/environment_setup.md. A local .venv directory is an ignored runtime artifact, not a submitted source file.

**Concepts learned:** interpreter versus environment, package installation, reproducible dependency versions, configuration validation, ignored secrets and meaningful version-control history.

**Expected output:** a repeatable environment in which the selected dependencies import and sample-mode settings load without live credentials.

**Completion checks**

- [ ] Record the interpreter version and installation procedure.
- [ ] Verify the resolved dependency set and record the versions actually checked.
- [ ] Missing/invalid settings produce clear errors; sample mode needs no API key.
- [ ] Real secrets, local databases, caches and the environment are excluded from staging.
- [ ] README setup steps correspond to commands that actually ran successfully.

**Boundary:** setting up an environment does not require downloading live cricket data or launching an unimplemented dashboard. Network/install permission issues must be reported as environment constraints rather than worked around with unverified version claims.

## M2 Database

**Objectives**

- Create a persistent sample database explicitly from the reviewed schema, without dropping or replacing an existing database by default.
- Implement centralized connection factories, foreign-key setup and transaction-scoped repository access.
- Add deterministic, labeled synthetic seed inputs that exercise the relationships and later SQL thresholds.
- Define useful supporting views and stored query definitions. A stored query here means a version-controlled SQL definition; it does not require database stored procedures.
- Establish source provenance, revision updates, validation and optimistic-version contracts needed by later ingestion and CRUD services.

**Files to implement or update:** utils/db_connection.py, database/initialize.py, database/repositories.py, models/records.py, utils/cricket.py, utils/dates.py, config.py, sql/schema.sql if justified by review, data/sample/README.md and README.md.

**Proposed new files:** sql/views.sql, data/sample/seed.json, tests/test_database.py, tests/test_validation.py, documentation/database_setup.md. The ignored database will live at data/runtime/sample.db. A live target is separately initialized only when needed and must not receive synthetic rows.

**Concepts learned:** schema creation, connections, transactions, constraints, composite foreign keys, views, source identities, legal balls, sample fixtures and query plans.

**Expected output:** a documented initialization operation builds the 21-table local schema and loads known sample records atomically; a restart retains them.

**Completion checks**

- [ ] Fresh initialization succeeds with foreign keys enabled on each connection.
- [ ] Re-initialization refuses destructive replacement and has a documented safe behavior.
- [ ] Sample/live mode mismatches are rejected before reading or writing the wrong dataset.
- [ ] Valid related records persist; wrong-team performances and duplicate provider identities are rejected.
- [ ] Failed multi-record operations roll back and do not advance the dataset revision.
- [ ] Unknown values remain NULL; 4.2 overs converts to 26 legal balls; invalid suffixes are rejected.
- [ ] A documented selection reads active, non-tombstoned records consistently.
- [ ] Supporting views and saved definitions load and return their declared columns.
- [ ] Record the SQLite compatibility result honestly; PostgreSQL/MySQL remain pending until checked.

**Sequence boundary:** complete this milestone before API implementation. Supporting database views must not solve Q01–Q25 early; those questions remain individual Phase 11 lessons.

## M3 API

**Objectives**

- Close the open provider/version and response-contract checks in the Phase 5 guide before hardcoding live requests or parsers.
- Implement the HTTP client, adapter and transactional ingestion path against that verified contract.
- Cover match lists, scorecards, player profiles/statistics and series data, with venue/team enrichment where supported.
- Bound requests, retries, pagination and refresh frequency using verified plan constraints.
- Keep career and series aggregates distinct, preserve partial updates and respect manual overrides/tombstones.

**Files to implement or update:** api/client.py, api/adapter.py, services/ingestion.py, services/matches.py, services/player_stats.py, models/records.py, database/repositories.py, config.py, .env.example, utils/logging_config.py and documentation/05_api_analysis.md.

**Proposed new files:** tests/test_api_client.py, tests/test_adapter.py, tests/test_ingestion.py, documentation/api_setup.md and sanitized response files plus provenance notes under tests/fixtures/.

**Concepts learned:** REST, authentication headers, requests sessions, response schemas, pagination, timeouts, retry budgets, idempotency, snapshot scope and freshness.

**Expected output:** one real provider match can be discovered, fetched, normalized and saved without duplicates; player/series capabilities have documented verified outcomes and coverage limitations.

**Completion checks**

- [ ] Provider/version, full URLs, input locations, headers, quota and historical access are recorded.
- [ ] Private credentials load outside source control; safe logs and fixtures contain no keys.
- [ ] A real match-list request and a scorecard request using its returned ID succeed; gateway mocks are distinguished.
- [ ] Supported player/stat and series requests succeed, with remaining required-data gaps explicitly resolved or recorded as unmet requirements.
- [ ] Reimporting a snapshot creates no duplicate logical records.
- [ ] Partial/older snapshots preserve newer known data; API refresh skips locked overrides and tombstones.
- [ ] HTTP calls occur outside write transactions; failed imports roll back and preserve the last successful snapshot.
- [ ] Authentication, rate-limit, timeout and malformed-data cases produce bounded, useful failures.
- [ ] Pagination terminates under the actual provider contract, including repeated-cursor protection where relevant.

**Open dependency:** no provider is selected. Fixture-based implementation can demonstrate internal behavior but does not complete live-integration acceptance. If access remains unavailable, record the blocker and obtain direction before changing the agreed phase order or claiming M3 complete. M4/M5 can technically use sample data, but this does not waive the required live deliverable.

## M4 CRUD

**Objectives**

- Implement create, read, update and logical delete for players and batting/bowling/fielding match-stat records.
- Enforce relationship validation, transaction ownership and optimistic version checks in services.
- Make API-owned edits explicit overrides; implement deliberate restoration/release behavior.
- Keep local operator permissions in the service layer, ready for a future public read-only mode.

**Files to implement or update:** services/players.py, services/match_stats.py, database/repositories.py, models/records.py and the supporting date/cricket helpers.

**Proposed new files:** tests/test_player_crud.py, tests/test_match_stats_crud.py and documentation/crud_guide.md. The actual Streamlit forms wait for M6.

**Concepts learned:** validation at boundaries, parameterized writes, transactions, soft deletion, referential integrity, ownership and conflicting edits.

**Expected output:** service-level player and match-stat operations work against the sample database and expose clear outcomes for later forms.

**Completion checks**

- [ ] Valid create/read/update/delete operations persist with the documented record grain.
- [ ] Invalid fields and wrong match/team/innings relationships leave the database unchanged.
- [ ] Update requires the expected version; stale writes are rejected rather than overwriting newer edits.
- [ ] API record edits become labeled overrides; logical deletion survives refresh attempts.
- [ ] Standard reads and joined analytics inputs exclude deleted players and performance tombstones.
- [ ] Each successful content change advances the revision once per logical transaction; rejected changes do not.
- [ ] Deleting referenced records physically is restricted; whole-match deletion is outside baseline CRUD.

## M5 Analytics

**Objectives**

- Teach and implement all 25 questions individually using the Phase 2 requirement inventory.
- For each question explain business purpose, SQL concepts, tables/relationships, logic, query, every line, plan and optimization; wait for NEXT before the next question.
- Resolve question-specific statistical definitions before coding the affected query.
- Build a saved-query registry and a restricted read-only custom SQL executor.

**Files to implement or update:** services/analytics.py, sql/queries/README.md and utils/db_connection.py for the restricted reader path.

**Proposed new files:** sql/query_registry.json; sql/queries/q01.sql through q25.sql, created one at a time; per-question lesson notes under documentation/sql/; tests/test_analytics.py and tests/test_query_executor.py. Engine-specific query variants are introduced only when that engine is implemented and verified.

**Concepts learned:** filtering, grouping, joins, CTEs, conditional aggregates, window functions, rolling form, standard deviation, ratios, eligibility thresholds and query-plan review.

**Expected output:** 25 documented, individually accepted queries return known results on controlled fixtures. Real-data outputs identify their actual coverage. Custom SQL has an independent restricted read path.

**Completion checks**

- [ ] Q01–Q25 each meet the exact output, date, ordering and eligibility requirements.
- [ ] Every query has an example fixture result and relevant boundary cases; an empty result is not treated as execution failure.
- [ ] Form/trajectory thresholds, deviation convention, T20 scope and denominators are explicit where required.
- [ ] Multiple Test innings do not inflate match counts; superseded snapshots, tombstones and super overs follow documented scope rules.
- [ ] Careers, series and imported match totals are never silently mixed.
- [ ] User parameters are bound separately from SQL text.
- [ ] Arbitrary SQL cannot write, attach writable databases or bypass reader restrictions; result and execution budgets are tested for the chosen engine.
- [ ] Representative plans are inspected and indexes adjusted only with evidence.

**Sequence boundary:** no analytical SQL is generated in Phase 7 or during the earlier database milestone. The optional extra query for the brief's 25+ wording follows the required 25 only if chosen.

## M6 Dashboard

**Objectives**

- Implement one page at a time in this order: Home, Live Matches, Top Players, Analytics, CRUD, Settings.
- Explain each page's purpose, components, inputs, outputs, backend logic and database calls before coding it.
- Add appropriate visuals, freshness/source labels, navigation and consistent error states.
- Consolidate exception behavior across the UI, services, database and provider.

**Files to implement or update:** main.py, the six existing pages/ modules, .streamlit/config.toml, config.py and existing services. Static styling belongs in assets/; screenshots are added to images/ during documentation.

**Proposed new files:** tests/test_ui.py and documentation/dashboard_guide.md. Create shared frontend helpers only if repetition justifies them.

**Concepts learned:** navigation, widgets, forms, session state, caching, cache invalidation, visual selection and translating service results into user feedback.

**Expected output:** a working Streamlit application with all four functional modules plus Home and Settings, using explicit sample/live modes.

**Completion checks**

- [ ] Every page is reachable and calls services rather than issuing its own SQL/HTTP requests.
- [ ] Live scores include detailed batting/bowling information and honest last-successful-refresh labels.
- [ ] Player leaderboards display their format, category, source and scope.
- [ ] Saved analytics show tables and meaningful eligibility/coverage feedback; custom SQL is restricted to the permitted operator.
- [ ] Player and match-stat forms support all four CRUD operations, validation and deliberate deletion confirmation.
- [ ] Successful writes refresh relevant tables/charts; reruns do not cause uncontrolled provider calls.
- [ ] Empty, stale, loading, invalid-input and unavailable states are usable.
- [ ] Settings displays no secret values and does not allow untrusted endpoint changes.
- [ ] Chart choices explain useful comparisons; do not force a pie chart or heatmap where it obscures the data.

## M7 Testing

**Objectives**

- Consolidate the checks added during implementation into a repeatable suite.
- Verify the integration between UI, services, repositories and adapters, not just isolated helpers.
- Separate deterministic fixture tests from optional authenticated smoke checks that consume provider quota.
- Review data quality and dialect claims against actual evidence.

**Files to update:** tests/test_database.py, tests/test_validation.py, tests/test_api_client.py, tests/test_adapter.py, tests/test_ingestion.py, tests/test_player_crud.py, tests/test_match_stats_crud.py, tests/test_analytics.py, tests/test_query_executor.py, tests/test_ui.py and tests/README.md.

**Proposed new files:** tests/conftest.py for genuinely shared fixtures, tests/test_integration.py, documentation/test_report.md and pytest.ini if test configuration is needed.

**Concepts learned:** unit versus integration tests, controlled fixtures, expected outputs, rollback isolation, mocking external failures and UI interaction verification.

**Expected output:** a reproducible test run plus a report identifying the runtime, dataset, passed/failed checks and unverified capabilities.

**Completion checks**

- [ ] A clean setup can reproduce the deterministic checks without live credentials.
- [ ] Tests use temporary databases and never alter the user's sample/live working database.
- [ ] One end-to-end fixture path imports a match, reads it, applies a correction and verifies affected analytical output.
- [ ] Negative cases cover constraints, partial imports, stale edits, provider failures and custom-SQL write denial.
- [ ] UI checks cover navigation, form validation and representative source/freshness states.
- [ ] All 25 queries have meaningful correctness evidence, including their stated thresholds.
- [ ] Authenticated smoke checks are separately labeled; fixture tests do not imply live verification.
- [ ] SQLite, PostgreSQL and MySQL each retain an explicit verified/unverified status.

**Boundary:** no arbitrary coverage percentage is a substitute for these acceptance checks. Add tests for important behavior and failure modes rather than tests that merely reproduce implementation details.

## M8 Deployment

**Objectives**

- Compare the requested hosting options in Phase 16 and select one appropriate target.
- Document dependencies, startup, secrets, database persistence, backup/restore and access mode for that target.
- Default public browsing to read-only; introduce verified authentication/authorization before allowing public administrative access.
- Prepare a reviewable deployment configuration before any external publication or paid-resource action.

**Files to implement or update:** README.md, requirements.txt, config.py, .streamlit/config.toml and .env.example.

**Proposed new files:** documentation/deployment_guide.md and documentation/deployment_verification.md. Create Dockerfile and .dockerignore only if Docker is selected. Create platform configuration only for the chosen host; no need to maintain speculative configurations for every provider.

**Concepts learned:** hosting versus local execution, secret injection, durable storage, database privileges, backups, access controls and operational smoke checks.

**Expected output:** tested deployment instructions and target-specific configuration. If deployment is authorized and performed, record the real application URL and smoke-check results; otherwise describe the package as prepared, not deployed.

**Completion checks**

- [ ] Target, persistence approach and access mode are explicit.
- [ ] Required secrets are injected privately and are not embedded in artifacts or logs.
- [ ] Database initialization does not overwrite existing data or seed sample rows into live mode.
- [ ] Restart behavior preserves the intended data; backup/restore steps are documented and verified where applicable.
- [ ] Public writes and custom SQL are disabled unless properly authorized and protected.
- [ ] Startup, navigation, one query and expected API failure behavior are verified in the target environment when deployed.
- [ ] Any cost, account, storage or live-data limitation is reported without claiming deployment success.

Actual deployment uses the user's authorization and the selected platform's available access. The milestones do not authorize a subscription purchase or publishing secrets.

## Submission follow-through after the eight milestones

Phase 17 updates installation, API/database setup, folder guide, screenshots and future improvements to match the implemented project. Prepare a recording script showing Home and all four functional modules, including player and match-stat CRUD. The recording deliverable remains incomplete until a playable walkthrough exists; writing a script alone does not complete it.

Phase 18 supplies 50 detailed interview/viva questions and answers covering the finished design, Python, SQL, Streamlit, APIs, testing and system design. Answers must reflect what was actually built and verified.

## Dependencies, timing and progress tracking

The technical path is M1 → M2 → M3 → M4 → M5 → M6 → M7 → M8, while tests and notes accompany each milestone. The provider-neutral sample database can be completed before selecting a live subscription. The learning sequence still requires finishing the database before API implementation and explicit phase confirmation throughout.

The original 14-day assignment target remains a planning estimate. Its start date is unknown, so no submission date can be calculated. The earlier plan allocates days 1–3 to design/structure, days 4–5 to database work, days 6–7 to API work, day 8 to CRUD, days 9–10 to SQL lessons, days 11–12 to pages/visuals, day 13 to consolidated checks/deployment preparation and day 14 to final documentation/demo/interview work. Actual progress depends on confirmation intervals, provider access and time spent learning each SQL question.

| Open issue | Affected milestone | Next resolution |
| --- | --- | --- |
| Environment and dependency versions unverified | M1 | Inspect available runtime and install/check a project-local environment during Phase 8 setup |
| No provider/version or plan selected | M3 | Complete the Phase 5 provider acceptance checklist before live implementation |
| Historical depth and fielding coverage unknown | M3, M5, M6 | Verify field mappings and dataset inventory; do not invent missing real data |
| Advanced statistical definitions unresolved | M5 | Set explicit conventions during each affected SQL lesson |
| SQLite-only design DDL verified | M2, M5, M8 | Adapt and check other engines before claiming support |
| Host, persistence and public access mode undecided | M8 | Decide during Phase 16 with a concrete deployment proposal |
| Assignment start date and final recording unknown | Submission | Record actual date when supplied; produce playable demo after functionality exists |

Milestones are marked complete only when their checks have evidence. A module file existing, a plan being written, or a synthetic response being parsed does not prove a working feature.

## Phase completion

**What we completed:** defined all eight requested milestones, including objectives, implementation/new file lists, learning concepts, expected outputs, completion checks, sequencing and unresolved dependencies.

**File created:** documentation/07_implementation_milestones.md. README.md now links to this plan and previews Phase 8; the requirements checklist marks LEARN-07 complete. Implementation milestones remain pending.

**Concepts learned:** milestones versus phases, dependency ordering, acceptance criteria, definition of done, evidence-based progress and separating live verification from fixture testing.

**Common mistakes to avoid:** marking implementation complete after planning, installing unverified dependency proposals blindly, skipping database validation, generating all SQL lessons at once, and confusing a prepared deployment package with a published working application.

**Next phase preview:** Phase 8 begins with the environment prerequisites in M1, then implements M2: central connections, reproducible initialization, sample data, relationships, indexes, views and supporting SQL definitions. We will explain each concept before code and complete database work before API implementation. Confirmation is required under the adopted mentoring prompt.

## Progress update after Phase 8

M1 environment setup and M2 local SQLite implementation are complete. See 08_database_implementation.md and 08_validation_report.md for files, setup and 64 passing checks. The status table above is the original Phase 7 planning snapshot. M3–M8 remain pending; database portability and provider access are not implied by this local result.

## Progress update during Phase 9

M3 now has implemented and tested provider-neutral transport, normalized ingestion, duplicate/freshness/ownership handling and a separate synthetic practice import. M3 remains incomplete pending provider/version selection, raw JSON mapping and authenticated live acceptance. The combined verification suite passes 136 checks. No later learning phase has started.

## Final Phase 9 acceptance

M3 is complete: authenticated match-list, regular scorecard, player profile/career and series capability checks passed. Profile and career ingestion, duplicate replay and atomic failure preservation are tested. The suite passes 188 tests. See 09_api_implementation.md and 09_phase_completion_result.json. Historical population, fielding totals and other data-coverage gaps are explicitly retained as unmet requirements; no archive completeness is claimed. Phase 10 has not started.

## Phase 10 acceptance

M4 CRUD is complete: player and batting/bowling/fielding services provide validated create/read/update/logical-delete/restore, version conflict protection, explicit API overrides and release. Public-readonly writes are denied. Thirty isolated CRUD checks pass within the full 218-test suite. See 10_crud_guide.md. Streamlit forms remain in M6; Phase 11 has not started.
