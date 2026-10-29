# Database setup and recovery

> Current status (2026-10-29): PostgreSQL/MySQL support and fresh quota/history verification are completed within the tested scope. See [remaining requirements completion](remaining_requirements_completion.md). Older phase checkpoints below are historical; the assignment deadline remains unverified.

## Two isolated datasets

SQLite is the default local engine; PostgreSQL 14.21 and MySQL 9.5.0 also passed actual server acceptance. See [server setup](database_compatibility.md). `data/runtime/sample.db` contains fictional training fixtures; `data/runtime/live.db` contains separately imported provider data. A database records its mode and must match the selected configuration. Never relabel sample data as live.

The preserved sample has schema 1, revision 1 and 18 explicit indexes. Fresh initialization creates schema 2, 21 tables, six views and 19 explicit indexes. Both schemas are readable; live ingestion needs schema 2. Opening the dashboard never migrates a database.

## Fresh targets and health checks

```sh
APP_ACCESS_MODE=local .venv/bin/python -m database.initialize --mode sample --database data/runtime/sample.db --seed-sample
APP_ACCESS_MODE=local .venv/bin/python -m database.initialize --mode live --database data/runtime/live.db
.venv/bin/python -m database.initialize --mode sample --database data/runtime/sample.db --check
.venv/bin/python -m database.initialize --mode live --database data/runtime/live.db --check
```

Run initialization only for absent targets. It refuses overwrites and cannot seed live mode. It builds transactionally in a temporary file and publishes without replacing an existing file. Existing sample contents remain unchanged when checked.

## Model and integrity

[Schema](../sql/schema.sql) and [ER design](04_database_design.md) describe teams, players, venues, series, matches, innings, participation, batting/bowling/fielding facts, career snapshots and source/import metadata. Provider external identities are source-scoped. Legal balls are stored as integers; displayed cricket overs are not decimal arithmetic. Unknown statistics remain NULL.

Read connections use SQLite read-only/query-only safeguards. Writes use explicit transactions with foreign keys and revision tracking. CRUD validates relationships and expected row versions; deletes are soft and API ownership requires explicit overrides. Current career views select the latest committed snapshot per source/exact format rather than adding snapshots together.

## Explicit schema 1 migration

Stop the app and other writers first. Verify the intended path and retain an independent SQLite-consistent backup before migration. For the sample target only:

```sh
DATA_MODE=sample DATABASE_URL=sqlite:///data/runtime/sample.db APP_ACCESS_MODE=local .venv/bin/python -m database.migrate
```

For a live target, explicitly substitute both DATA_MODE=live and its live DATABASE_URL. The migration has no path flags; it reads configuration. It creates a no-overwrite `.v1-backup` beside the target and applies additive schema 2 atomically. An existing backup filename causes refusal; preserve it and investigate rather than deleting it blindly. Schema 2 is a no-op. Do not migrate the preserved teaching sample merely to browse it.

## Backup and restore

Use SQLite's backup API for a consistent backup, or stop every connection before copying a closed database. Do not copy a live database while ignoring possible journal/WAL companions. Keep backups outside public packages. To restore, stop the app/writers, preserve the current failed target separately, restore the chosen consistent backup to the configured path, then run the matching --check command before reopening. Verify source/mode/schema and counts in Settings. Recovery is an operator task, never automatic reseeding.

## SQL and limitations

Analytics offers 26 reviewed analyses and restricted local custom read-only SQL with statement/function checks, time and output budgets. Public-readonly mode disables custom SQL and writes; it does not authenticate users. Views hide soft-deleted facts. Sample analysis uses 2026-10-01; provider history is partial and was expanded on 2026-10-29. PostgreSQL/MySQL support is now accepted on the tested versions; see database_compatibility.md. Multi-instance hosted writable SQLite remains unaccepted. See [testing](15_testing.md) and [deployment](16_deployment.md).
