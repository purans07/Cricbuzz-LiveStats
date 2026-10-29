# Phase 8 Environment and database implementation

The project now has a checked local Python environment and a persistent sample SQLite database. This completes the local database milestone while retaining the later learning sequence for API, CRUD, analytics and dashboard work.

## Step 1 Environment and configuration

A virtual environment separates project dependencies from the system interpreter. Direct dependencies and the full resolved dependency set are recorded in requirements files. config.py loads optional private .env settings and environment overrides, validates mode/timezone/access, and resolves local SQLite paths.

The environment uses Python 3.13.5. Dependency import checks and pip's consistency check succeeded. Streamlit, pandas, requests and Plotly are installed for later work; their application features are not implemented yet. See environment_setup.md for reproduction.

## Step 2 Central connections and transactions

utils/db_connection.py is the single connection entry point. Each operation opens a fresh connection, enables foreign keys and checks the dataset mode/schema version. Read connections open the existing file read-only; write operations require local access mode.

A transaction groups related changes. Successful writes commit and advance the revision once; an exception rolls back changes and the revision. No HTTP work occurs here. Opening a missing database never silently creates an empty file.

## Step 3 Safe database creation

database/initialize.py applies the reviewed Phase 4 DDL and supporting views in an initializer-owned temporary database. It inserts the mode marker and optional sample seed, validates relationships/integrity, and publishes only a completed file. Atomic no-overwrite publication protects existing databases and concurrent initialization attempts.

The original schema.sql remains a creation script. Schema version 1 is recorded with SQLite user_version rather than adding a 22nd table. Every application connection rejects a different version; no automatic destructive migration is performed.

## Step 4 Labeled sample data

data/sample/seed.json provides 12 fictional players, two sample national sides, two venues, 12 series, 72 matches across three formats and 12 quarters, 192 innings, and 1,152 rows in each performance table. Two snapshot batches provide 72 career rows in total; the latest view returns 36 player/format snapshots.

The data's fixed analysis date is 2026-10-01. It is explicitly synthetic, uses simplified six-player scorecards, and is a database exercise rather than a realistic match simulator. No real player statistics or live API responses have been imported. Sample/live targets remain separate.

## Step 5 Views and stored definitions

sql/views.sql defines six active-record and latest-snapshot views. Active performance views exclude tombstones, deleted players and super overs. Latest career data is selected independently per source from committed batches, without summing snapshots.

Two allowlisted operational SQL files read dataset status and a player by ID. They support persistence checks without solving the Phase 11 assignment questions. PlayerRepository implements active reads and a version-checked patch primitive; the service-level CRUD rules remain Phase 10 work.

## Step 6 Data validation

models/records.py rejects unexpected columns, fractional/boolean integer counts, negative counts, invalid dates, non-finite ratios and blank player names in supported input paths. Unknown values remain distinct from zero.

utils/cricket.py converts overs notation into legal balls: 4.2 → 26. It rejects floats and impossible ball suffixes. utils/dates.py requires timezone-aware timestamps and stores canonical UTC values, then converts them for local display.

## Step 7 Verification

The database suite uses a session template copied into independent temporary databases for each test. It never modifies the user's working sample database. Checks cover bootstrap failure cleanup, existing-file preservation, constraints, transaction rollback/revisions, persistence on reconnect, read-only mode, wrong-mode/schema rejection, tombstones, latest snapshots, bound values, stale versions and a representative indexed access plan.

Validation evidence and exact check counts are in 08_validation_report.md. No SQL assignment question is marked implemented. No HTTP requests were made to a cricket provider.

## Milestone boundaries

M1 environment setup and M2 local SQLite implementation are complete subject to the recorded validation evidence. Database-agnostic design remains documented, but PostgreSQL and MySQL have not been implemented or tested. Full service ownership enforcement, public authentication, arbitrary-SQL sandboxing and the Streamlit dashboard remain later work.

## Phase completion

**What we completed:** project-local environment; pinned direct dependencies and resolved lock; validated configuration; central reader/writer connections; safe initialization; persistent synthetic sample database; six views; two operational stored queries; repository foundations; date/cricket validation; automated database checks; and project-local Git tracking.

**Files created or updated:** configuration and requirements files, utils/db_connection.py, utils/cricket.py, utils/dates.py, models/records.py, database/initialize.py, database/repositories.py, sql/views.sql, two operational SQL files, data/sample/seed.json, tests/conftest.py, tests/test_database.py, tests/test_validation.py, pytest.ini, ruff.toml and setup/phase guides. The working database is ignored under data/runtime/sample.db.

**Concepts learned:** virtual environments, dependency locking, validated configuration, transactions, referential integrity, atomic initialization, mode isolation, views, bound parameters, concurrency versions, and fixture-based verification.

**Common mistakes:** overwriting an existing database, silently creating a missing database, trusting default SQLite type affinity, using sample records as real statistics, summing snapshots, manually committing inside a managed transaction, and treating internal reader connections as a complete arbitrary-query sandbox.

**Next phase preview:** Phase 9 implements API requests, response normalization and ingestion after selecting and verifying a provider/version. No provider has been selected yet; live implementation remains dependent on the Phase 5 acceptance checks. The adopted mentoring prompt requires confirmation before proceeding.
