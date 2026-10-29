# Database support

SQLite, PostgreSQL and MySQL are implemented. Actual acceptance servers used PostgreSQL 14.21 and MySQL 9.5.0; SQLite remains the default. See [completion evidence](remaining_requirements_completion.md).

| Feature | SQLite | PostgreSQL | MySQL |
| --- | --- | --- | --- |
| Schema and sample initialization | Supported | Schema 2 | Schema 2 |
| All 26 analytical questions | Tested | Results compared to SQLite | Results compared to SQLite |
| Player/statistics CRUD and imports | Tested | Tested | Tested |
| Read protection | File readonly + authorizer | Separate SELECT-only role + readonly transaction | Separate SELECT-only user + readonly transaction |
| Six dashboard pages | Tested | Tested | Tested |

## Configure a server

Install dependencies from requirements-lock.txt. An operator must create an empty database and two private accounts: a writer owning the application schema and a reader with SELECT only. Set private DATABASE_URL and READ_DATABASE_URL to the same host, port and database, using distinct users. PostgreSQL uses `postgresql+psycopg://`; MySQL uses `mysql+pymysql://`. Never commit actual passwords. The application verifies reader privileges and rejects a privileged reader. PostgreSQL readers also must lack database CREATE/TEMP and public schema CREATE privileges; revoke PUBLIC defaults where necessary.

For a synthetic teaching database set DATA_MODE=sample and run:

```bash
python -m database.server --seed-sample
```

For a live database set DATA_MODE=live and run `python -m database.server` without the seed flag. Initialization refuses nonempty databases. Existing SQLite files are preserved; this command does not copy their records. MySQL DDL is not transactional: a failed bootstrap can leave partial objects requiring operator investigation in that newly created database.

Server schema versions are stored in dataset_state; the SQLite file migration command is intentionally separate. Server writes lock the dataset revision row, preserve atomic imports and optimistic row versions, and roll back failures. Reads use repeatable-read snapshots, timeouts and bounded output. Reviewed SQLite analytical SQL is translated for each server dialect and result equivalence is tested.

TLS options are accepted through validated driver URL options (PostgreSQL sslmode/certificate paths; MySQL ssl_ca/certificate verification). External TLS hosting was not acceptance-tested. Physical server backup/restore, additional engine versions and multi-instance production deployment remain operational follow-ups. The packaged public demo continues to use SQLite; the main dashboard supports all three engines.
