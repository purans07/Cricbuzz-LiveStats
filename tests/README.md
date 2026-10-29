# Database verification

Run from the project folder:

```sh
.venv/bin/python -m pytest -q
```

The suite initializes a synthetic template under pytest's temporary directory and copies it for each database test. It does not modify data/runtime/sample.db or use live credentials. It checks initialization safety, persistence, SQL constraints, transaction rollback/revisions, mode separation, active views, snapshot selection, parameter binding, optimistic versions and primitive/date/cricket validation.

Tests are deterministic and make no provider requests. Further API, service CRUD, assignment SQL and UI tests accompany their implementation phases. Sanitized captured responses belong in tests/fixtures with origin/version/capture metadata; they must never include credentials.
