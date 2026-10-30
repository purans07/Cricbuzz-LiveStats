# Cricbuzz LiveStats

[Public API-backed website](https://cricbuzz-livestats-web.streamlit.app/). The public view now uses verified provider records and a daily backend match-list refresh. It remains read-only; imported coverage is limited and updates are not continuous live scoring. [Deployment details](documentation/public_provider_deployment.md).

Current verification: SQLite, PostgreSQL 14.21 and MySQL 9.5.0 are supported and tested. Dated API verification expanded saved history; account quota is historical evidence, not a current balance. The assignment deadline remains unknown. See [completion report](documentation/remaining_requirements_completion.md).

A Python, SQLite and Streamlit dashboard for saved cricket scores, player statistics, 26 SQL analyses and validated administrative CRUD. Interactive Plotly charts explain ranking, consistency, venue performance and quarterly trends.

## Start with the sample

The checked environment is Python 3.13.5 on macOS. Run from the project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
APP_ACCESS_MODE=local .venv/bin/python -m database.initialize --mode sample --database data/runtime/sample.db --seed-sample
DATA_MODE=sample DATABASE_URL=sqlite:///data/runtime/sample.db APP_ACCESS_MODE=local .venv/bin/python -m streamlit run main.py --server.address 127.0.0.1
```

Initialize only a fresh target: the initializer refuses to overwrite existing databases. If the sample already exists, replace initialization with the same command using `--check` instead of `--seed-sample`. Open [the local dashboard](http://127.0.0.1:8501). Sample mode needs no API key. Process settings above override any private .env values.

## Explore the application

| Page | Purpose |
| --- | --- |
| Home | Saved dataset counts, provenance and downloadable guides |
| Live Matches | Saved match filters, innings and scorecards; explicit provider refresh |
| Top Players | Latest career rankings, profiles and player comparisons |
| Analytics | 26 saved SQL analyses, charts and restricted local custom SQL |
| CRUD | Validated player and batting/bowling/fielding fact editing |
| Settings | Read-only diagnostics and session display timezone |

Browsing and filtering use saved data. Provider calls run through explicit local refreshes or the scheduled backend job. `main.py` is for trusted local operators; `cloud_app.py` serves the public read-only provider-backed website (or an explicitly selected fictional sample). Access mode is an application policy, not user authentication.

## Documentation

- [Installation and environment](documentation/environment_setup.md)
- [User guide and troubleshooting](documentation/user_guide.md)
- [Current folder map](documentation/folder_guide.md)
- [API configuration and imports](documentation/api_setup.md)
- [Database setup, migration and recovery](documentation/database_setup.md)
- [Screenshots section](documentation/screenshots/README.md)
- [Future improvements](documentation/future_improvements.md)
- [Deployment preparation](documentation/16_deployment.md)
- [Documentation index and all phase lessons](documentation/README.md)

## Data and acceptance limits

The fictional sample has 12 players, 72 matches, 192 innings and 12 quarters; its fixed analysis date is 2026-10-01. It teaches SQL and does not represent professional cricket results. Existing sample schema 1 remains supported; fresh initialization creates schema 2.

Saved provider data was expanded on 2026-10-29. It contains 87 matches, 199 innings, partial scorecards and career enrichment for three players. It is neither a complete historical database nor a global leaderboard. Missing values remain unknown. Current-world scores require a successful explicit refresh. The selected integration is RapidAPI cricketapilive/cricbuzz-cricket v2; reviewed routes include v1 URLs.

All 18 teaching phases are documented. Final validation on 30 October 2026: **664 tests passed**, including SQLite, PostgreSQL and MySQL integration checks; lint and formatting passed. All six hosted pages rendered without application exceptions. The public site uses saved provider data with daily backend updates and deliberately disables writes and visitor API calls. See [the final submission guide](SUBMISSION.md) for deliverables, evidence and limitations.

## Verify locally

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

Tests use temporary databases and mocked HTTP; no credentials are needed. Historical validation reports retain their original test counts. Keep private .env, raw responses, runtime databases and credentials out of Git and public deployment packages.

## Requirements and submission

[Current submission assessment](SUBMISSION.md) · [Dated requirement audit](documentation/requirements_audit.md) · [Screenshots](documentation/screenshots/README.md) · [Walkthrough video](documentation/demo/README.md). The original 25 SQL questions plus Q26 coverage analysis are available. PostgreSQL/MySQL runtime support and dated quota/history verification are completed within the observed scope. The assignment deadline remains unverified.
