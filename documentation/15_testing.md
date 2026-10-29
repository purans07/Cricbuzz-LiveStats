# Phase 15 — Testing

Phase 15 organizes the project's existing tests into a practical strategy, adds cross-module acceptance journeys, blocks accidental real requests during automated tests, and records reproducible suite evidence. Phase 16 deployment has not started.

## Testing concepts explained before implementation

A useful test checks observable behavior and a meaningful failure boundary, not merely that the implementation calls itself. Choose the smallest appropriate scope and use isolated fixtures so validation does not alter working records or spend provider quota. A passing suite proves its stated cases, not complete correctness, production readiness, complete historical coverage or compatibility with untested database engines.

| Test type | Purpose | Project examples | Limits |
| --- | --- | --- | --- |
| Unit | Verify a small rule/function independently | Cricket overs conversion, strict values/dates, safe error classification, chart gaps/identities | Does not prove real database or provider integration |
| Integration | Verify collaborating modules and transaction boundaries | Normalizer → ingestion → SQLite; CRUD → active views → analytics/chart; latest career → leaderboard | Uses fixtures and a local SQLite engine |
| Database | Verify schema, constraints, rollback, mode isolation and query semantics | Foreign keys, duplicate imports, stale versions, read-only SQL, all 25 questions | Does not establish PostgreSQL/MySQL compatibility |
| API | Verify transport policy and provider-contract adaptation | Injected responses for authentication, 429, timeout, JSON, provenance and captured match/player responses | Does not authenticate a current key or validate a paid subscription |
| UI | Verify actual Streamlit script/form/rerun behavior | Six routes, filters, CRUD confirmation, protected forms, source labels, safe errors and chart rendering | AppTest does not perform pixel layout, accessibility or real-browser JavaScript acceptance |
| Acceptance journey | Verify a user-relevant path across modules | Create/update/delete/restore statistics and see active results; import careers, rank/chart, preserve API-owned tombstones | In-process automated acceptance, not hosted end-to-end infrastructure testing |

The categories overlap. For example, an AppTest form that commits through a real temporary SQLite database is both UI and integration coverage. Per-file counts in the execution report are an inventory, not a coverage percentage.

## Isolation and fixtures

`tests/conftest.py` creates one session-scoped seeded schema-2 sample template in a temporary directory, then copies it for each test. Database fixtures dispose engines in finally/yield cleanup. Individual import tests create additional empty temporary databases where appropriate. This avoids repeated expensive seeding while keeping mutations independent.

The original working sample is preserved at schema 1 and the saved provider target at schema 2; tests never use them for mutations. Tests that deliberately violate relationships or delete fixture rows operate on disposable copies. Schema/migration tests use their own targets and backups. No initializer is run against an existing working file merely to make a test pass.

The new autouse fixture blocks the real requests Session.send path by default. Tests inject an HTTP double or explicitly patch a transport boundary. A regression test confirms that an otherwise unmocked requests.get fails at the guard before a real send. This protects against accidental provider quota use, not every possible networking API in Python; it is not an operating-system network sandbox. Do not bypass the guard to turn a unit test into an undocumented live request.

Do not paste real keys into test fixtures or assertions. API tests use placeholder credentials and captured/synthetic JSON. Private configuration remains outside evidence reports. Do not enable HTTP wire logging to debug a test with a real key.

## Requirement-to-evidence matrix

| Requirement area | Automated evidence | Important remaining boundary |
| --- | --- | --- |
| Values/cricket units/configuration | test_validation.py | Local configured environment only |
| Schema, mode isolation and migrations | test_database.py, test_migration.py | SQLite supported; other engines unverified |
| Transport and provider mappings | test_api_client.py, test_cricbuzz_v2.py, test_scorecard.py, test_player_api.py | Captured responses and doubles, not a fresh live call |
| Atomic ingestion, freshness and duplicates | test_ingestion.py, test_live_sync.py, test_acceptance_journeys.py | Limited imported history, no archive completeness claim |
| Player/stat CRUD, ownership and stale versions | test_player_crud.py, test_match_stats_crud.py, test_crud_page.py | Local trusted operator; no public administrative authentication |
| Q01–Q25 definitions and SQL boundaries | test_q01.py through test_q25.py | Fixture/query correctness, not proof of sufficient live fields/history |
| Guarded custom SQL and all saved questions | test_analytics_page.py | Local cooperative limits, not an OS sandbox |
| Sample/provider provenance and real page forms | test_home.py, test_live_matches_page.py, test_top_players.py | Fresh authenticated UI refresh remains explicit operator acceptance |
| Timezone, diagnostics and six-page navigation | test_settings_page.py | Session preferences, not persistent configuration editing |
| Chart grain/units/gaps and actual Streamlit rendering | test_visualizations.py | Plotly trace correctness, not pixel/browser acceptance |
| Safe error recovery and control flow | test_error_handling.py | Startup failures before app dependencies load remain deployment issues |
| Cross-module business journeys | test_acceptance_journeys.py | Temporary SQLite/in-process paths; not a hosted acceptance run |

The requirements checklist is updated only for behaviors supported by these cases. It does not mark deployment, recording, global leader population, ball-by-ball partnerships or trained predictions complete.

## New acceptance journeys

### Player/statistics lifecycle → analytics/overview

Create a manual profile, establish fixture participation in a disposable database, create a batting row, update its score and read it through the active analytics path. Verify the overview count increases. Soft-delete the profile and confirm its statistic disappears from active reads; restore and confirm visibility returns. Soft-delete/restore the statistic independently and verify its stored value remains correct. Check foreign-key integrity at the end.

The fixture's participation setup is deliberate test preparation, not a new match-participation UI feature. Only the selected profile/statistics identities are mutated. Known results are asserted instead of copying the implementation's arithmetic as a test oracle.

### Captured normalized import → career ranking/chart → ownership lifecycle

Import a synthetic normalized graph into a new temporary sample database. Replaying the exact snapshot must report duplicate and leave revision unchanged. Feed its latest career rows into TopPlayersService and verify chart values equal the ranked SQL values.

An imported profile is API-owned under ingestion policy even when the dataset is a synthetic fixture. A deletion without explicit override must fail; the test correctly honors that policy rather than weakening it. Delete with override, import a newer snapshot and confirm the protected profile remains absent from the active leaderboard. Restore the override and confirm it reappears. Verify foreign keys remain valid.

These journeys add evidence that state transitions remain consistent across modules. Existing focused tests still provide more detailed boundary cases and precise failure localization.

## Meaningful sample test cases

| Case | Preparation/action | Expected result |
| --- | --- | --- |
| Blank versus zero | Submit blank runs, then known zero where allowed | NULL and zero remain distinct |
| Overs units | Convert 4.2 overs and reject float 4.2 | 26 balls; floats rejected |
| Wrong relationship | Create bowling stats for the batting side | Rejected atomically; revision unchanged |
| Stale edit | Load form, commit another edit, submit old version | Conflict message; newer value preserved |
| Confirmed delete | Submit deletion with/without confirmation | No change without confirmation; reversible tombstone after confirmation |
| API override | Edit/imported profile without/with override | Ownership denial, then protected override |
| Duplicate import | Replay identical captured snapshot | No duplicated records or revision bump |
| Failed import | Introduce malformed/invalid linked data | Whole import rejected; prior saved snapshot remains |
| Rate limit | Inject 429 with Retry-After | Safe message and cooldown; no uncontrolled repeat request |
| Invalid JSON | Inject wrong content type/malformed body | Typed safe failure; no fabricated empty success |
| Custom write | Submit DELETE, ATTACH, PRAGMA or chained statements | Reader rejection; data/revision unchanged |
| Missing history | Run six-quarter/five-head-to-head chart/query on sparse data | Explained empty output; no invented rows |
| Quarter gap | Supply Q4 and Q2 with missing Q1 | Blank gap; no connected line or zero-filled heatmap cell |
| Navigation | Visit all six routes without actions | No implicit HTTP or write/revision changes |
| Unexpected page error | Inject runtime/Streamlit error then rerun healthy page | Safe recovery message, no private details; normal rendering recovers |

## Running the suite

From the project folder, use the checked virtual environment:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pip check
```

Focused examples:

```sh
.venv/bin/python -m pytest tests/test_validation.py -q
.venv/bin/python -m pytest tests/test_database.py tests/test_migration.py -q
.venv/bin/python -m pytest tests/test_api_client.py tests/test_player_api.py -q
.venv/bin/python -m pytest tests/test_crud_page.py tests/test_settings_page.py -q
.venv/bin/python -m pytest tests/test_acceptance_journeys.py -q
```

To capture machine-readable results without placing temporary raw output in the repository:

```sh
.venv/bin/python -m pytest -q --junitxml=/tmp/cricbuzz-tests.xml
```

Use module execution with the project's interpreter. A globally installed pytest/streamlit can use different paths or package versions. Do not add retries or reorder tests merely to hide nondeterministic failures. Reproduce a failing case independently, correct the implementation or fixture, then run affected checks and the final suite once the changes settle.

## Final evidence and limits

[The validation report](15_validation_report.json) records actual suite counts, pass/fail/skip status, per-test-file counts/times, interpreter/SQLite versions and independent lint/format/whitespace/dependency results. It is derived from the final JUnit run rather than a hand-counted test list. Working sample/live database file fingerprints were compared immediately before and after that run; the report records whether they match. This is additional evidence for the observed run, not permission to point future mutation tests at those files.

Final result: **513 tests passed**, with no failed or skipped tests. Lint, formatting, whitespace and installed dependency checks pass. All three new acceptance/guard checks pass. No statement coverage percentage is claimed because no coverage instrumentation was run. A large test count does not prove every branch or deployment condition is covered.

Manual/operational acceptance still includes fresh authenticated provider calls when deliberately requested, real-browser responsive/keyboard/contrast checks, hosted persistent storage, deployment secrets and startup, public administrative access design if writes are exposed, walkthrough recording and final submission review. Historical live-data coverage remains incomplete; fictional fixture success does not remove it. Automatic CI, load testing and cross-engine compatibility checks are not introduced in this phase.

## Phase completion

**What we completed:** explained unit/integration/database/API/UI testing, mapped requirements to evidence, added two cross-module acceptance journeys and a verified default HTTP guard, and produced final machine-readable test results plus working-data isolation evidence.

**Files created/changed:** tests/test_acceptance_journeys.py, tests/conftest.py, this guide, documentation/15_validation_report.json, README, requirements progress and the sidebar next-phase preview.

**Concepts learned:** test scope, fixtures, reproducibility, transaction/ownership invariants, adverse cases, transport injection, JUnit evidence, test counts versus code coverage and automated versus live/hosted acceptance.

**Next phase preview:** Phase 16 — Deployment will compare Streamlit Community Cloud, Render, Railway, Azure, AWS and Docker, prepare a suitable deployment path and document persistence/secrets/read-only constraints. Publishing or purchasing services is separate from preparing reviewable deployment files. Phase 15 is complete; advance after the next user request.
