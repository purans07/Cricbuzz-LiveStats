# Phase 8 Validation report

Verification date: 21 October 2026 (Asia/Kolkata).

## Environment

- Python: 3.13.5
- SQLite: 3.50.2
- Platform: Darwin x86_64
- Environment: project-local .venv
- Dependency consistency: pip check passed with no broken requirements.
- Direct runtime package import checks: all six passed.

| Package | Installed version |
| --- | --- |
| SQLAlchemy | 2.1.5 |
| streamlit | 1.66.0 |
| requests | 2.34.2 |
| pandas | 3.0.6 |
| plotly | 7.1.0 |
| python-dotenv | 1.2.4 |
| pytest | 9.1.1 |
| ruff | 0.17.1 |

All runtime packages imported. The sandbox emitted PyArrow CPU-cache inspection diagnostics during import; imports still completed successfully. Streamlit/pandas/Plotly application behavior is not yet tested. requirements-lock.txt records the installed environment.

## Automated checks

- pytest: **64 passed**, no failures, in the final run.
- Ruff lint: passed.
- Ruff formatting: all 47 project Python files already formatted in the final check.
- Git ignore checks: private .env, Streamlit secrets, virtual environment, working database and logs are excluded.

The suite uses private temporary databases. It verifies configuration and date/ball validation, atomic initialization failure cleanup, existing-file preservation, sample/live isolation, unsupported schema rejection, foreign keys, invalid relationship rejection, physical delete restrictions, transaction rollback, one revision increment per successful write transaction, persistence on reconnect, read-only operations, public-mode write rejection, tombstones, super-over exclusions, latest committed snapshots by source, parameter binding, optimistic versions and a representative index plan.

## Working sample database inspection

Read-only inspection returned:

```json
{
  "mode": "sample",
  "revision": 1,
  "tables": 21,
  "views": 6,
  "indexes": 18,
  "players": 12,
  "matches": 72,
  "innings": 192,
  "career_stats_snapshots": 72,
  "foreign_keys": 1,
  "integrity": "ok"
}
```

Each of the batting, bowling and fielding tables has 1,152 fixture records. They are fictional simplified training records, not factual professional scorecards. The 72 career rows contain two batches; the latest view returns 36 snapshots. The sample database's recorded mode is sample and its baseline revision is 1. No live database has been created in the working project.

## Limits

Only SQLite on the recorded Python/platform combination is verified. PostgreSQL/MySQL, provider authentication, real historical coverage, full CRUD services, all 25 assignment queries, arbitrary-SQL sandboxing, dashboard interaction and deployment are unimplemented or unverified. Repository-level version checks are working; business-level override handling belongs to subsequent services.

The original 25 Phase 4 schema checks remain historical design-stage evidence. This report covers the new implementation suite and does not add those old check counts to inflate the current test result.
