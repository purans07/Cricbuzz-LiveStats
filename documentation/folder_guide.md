# Current folder map

| Path | Responsibility |
| --- | --- |
| main.py | Trusted local Streamlit navigation |
| cloud_app.py | Public read-only provider/sample entry |
| config.py | Validated mode, path, timezone and access settings |
| pages/ | Six navigation page entry points |
| ui/ | Page presentation, preferences, error boundaries and visualizations |
| services/ | Imports, CRUD, saved match/player reads and analytics execution |
| api/ | Reviewed provider contracts, HTTP client, adapters and CLI |
| database/ | SQLite initialization/migration and PostgreSQL/MySQL schema-2 initialization |
| sql/schema.sql, sql/migrations/ | Schema and version changes |
| sql/queries/ | 26 analytical analyses and supporting SQL |
| utils/ | Database connections, dates, charts and safe logging |
| data/sample/ | Reviewed fictional seed inputs |
| data/runtime/ | Ignored local databases; preserve separately |
| data/raw/ | Ignored private capture workspace; never publish credentials |
| tests/ | Unit, integration and Streamlit acceptance checks with fixtures |
| documentation/ | Current operational guides and historical phase evidence |
| deployment/ | Public provider snapshot import and optional sample bootstrap |
| .streamlit/ | Theme and example settings; private secrets stay ignored |
| Dockerfile, .dockerignore, compose.yaml | Reviewed demo packaging and loopback launch |
| requirements*.txt | Runtime, development and resolved dependency lists |

Typical flow: page → UI → service → database. Explicit refresh goes through the reviewed API client and normalizer into transactional ingestion, then the UI reads committed data. Charts consume saved results. Supplied Word briefs and Retail_Arcade.html are reference materials outside runtime. Earlier [Phase 6 map](06_project_structure.md) records the original scaffold.
