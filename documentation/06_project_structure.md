# Phase 6 Project folder structure

The project now has physical folders and placeholder modules matching the Phase 3 architecture. The original reference files, existing guides and validated SQL schema are preserved. This scaffold separates responsibilities before database, API and interface code is introduced in the agreed learning sequence.

## Folder tree

```text
project/
├── main.py
├── config.py
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── api/
│   ├── __init__.py
│   ├── client.py
│   └── adapter.py
├── database/
│   ├── __init__.py
│   ├── initialize.py
│   └── repositories.py
├── models/
│   ├── __init__.py
│   └── records.py
├── services/
│   ├── __init__.py
│   ├── matches.py
│   ├── player_stats.py
│   ├── ingestion.py
│   ├── players.py
│   ├── match_stats.py
│   └── analytics.py
├── pages/
│   ├── 01_Home.py
│   ├── 02_Live_Matches.py
│   ├── 03_Top_Players.py
│   ├── 04_Analytics.py
│   ├── 05_CRUD.py
│   └── 06_Settings.py
├── utils/
│   ├── __init__.py
│   ├── db_connection.py
│   ├── cricket.py
│   ├── dates.py
│   └── logging_config.py
├── sql/
│   ├── schema.sql
│   └── queries/README.md
├── data/
│   ├── sample/README.md
│   ├── raw/README.md
│   └── runtime/.gitkeep
├── tests/
│   ├── README.md
│   └── fixtures/.gitkeep
├── assets/.gitkeep
├── images/.gitkeep
├── logs/.gitkeep
└── documentation/
    ├── 01_project_understanding.md
    ├── 02_requirement_analysis.md
    ├── 03_system_design.md
    ├── 04_database_design.md
    ├── 04_schema_validation.md
    ├── 05_api_analysis.md
    └── 06_project_structure.md
```

The supplied Cricbuzz.docx, Prompt to be used in Claude.docx and Retail_Arcade.html also remain in the project root. They are reference material and are omitted from the runtime tree above for clarity.

## Why each folder exists

| Location | Responsibility | Implementation phase |
| --- | --- | --- |
| main.py | Assemble application dependencies and page navigation; currently prints scaffold status only | 12 |
| config.py | Load and validate settings centrally | Environment/database/API milestones |
| api/client.py | HTTP session, auth, timeouts and bounded retries | 9 |
| api/adapter.py | Translate verified provider JSON into normalized records | 9 |
| database/initialize.py | Reproducible schema and sample-data initialization | 8 |
| database/repositories.py | Parameterized data access on transaction-scoped connections | 8, extended in 10 |
| models/records.py | Define record contracts and reusable validation | 8–10 |
| services/matches.py | Match-list, detail and refresh coordination | 9 |
| services/player_stats.py | Scoped leaderboards and career snapshots | 9 |
| services/ingestion.py | Identity resolution, import ordering, ownership and completeness rules | 9 |
| services/players.py | Player CRUD validation and transaction orchestration | 10 |
| services/match_stats.py | Batting, bowling and fielding CRUD rules | 10 |
| services/analytics.py | Saved SQL dispatch and restricted custom query execution | 11 |
| pages/ | Six frontend views; no direct SQL connections or HTTP calls | 12 |
| utils/db_connection.py | The centralized connection entry point explicitly required by the assignment | 8 |
| utils/cricket.py | Legal-ball conversion and other small cricket helpers | Alongside relevant implementation |
| utils/dates.py | Validate dates and convert storage/display timestamps | Alongside relevant implementation |
| utils/logging_config.py | Configure logs without credential exposure | Alongside relevant implementation |
| sql/schema.sql | Existing Phase 4 SQLite creation statements | Designed in 4; initialization in 8 |
| sql/queries/ | Reviewable Q01–Q25 solutions, one at a time | 11 |
| data/sample/ | Clearly labeled synthetic seed input files | 8 |
| data/raw/ | Private local response inspection; ignored except its guide | 9 |
| data/runtime/ | Local sample/live database files; contents ignored | 8 onward |
| tests/fixtures/ | Sanitized captured responses and labeled synthetic inputs | 8 onward |
| tests/ | Meaningful checks accompanying implementation; broader review in Phase 15 | 8–15 |
| assets/ | Shared static interface assets and styling | 12–13 |
| images/ | Documentation screenshots | 17 |
| logs/ | Local diagnostic output excluded from version control | Implementation phases |
| documentation/ | Phase guides, design evidence and setup notes | All phases |
| .streamlit/ | Project settings and a secret template | Settings in 12; private configuration as needed |

## Root files and configuration

README.md is the project's current entry guide. It states the scaffold's limits and links to every completed phase. requirements.txt and requirements-dev.txt contain commented dependency candidates; versions and environment setup have not been finalized. They are deliberately not presented as working installation instructions.

.env.example names the proposed configuration contract and uses an explicit sample database path. The live database uses a separate path when later selected. No .env loader exists yet. Likewise, secrets.toml.example is a template and contains no real credential; it does not become active merely by existing.

.gitignore excludes private environment files, Streamlit secrets, virtual environments, caches, local databases, raw responses and logs. Reviewed synthetic samples and sanitized fixtures can remain version controlled. No Git repository has been initialized in this phase; repository setup belongs in the implementation milestone plan.

## Packages and placeholders

The api, database, models, services and utils folders have __init__.py files so they form explicit Python packages. Their modules contain explanatory docstrings rather than simulated operations. No placeholder reports an API call, database write or analytical query as successful.

The page filenames provide a readable order for the six planned views. Their code is intentionally not implemented. Running the entry point prints a status message; it does not launch a dashboard. No external library is needed for this scaffold status check.

.gitkeep is an empty marker used to retain an otherwise empty folder when Git is introduced. It is not application data or configuration.

## Module dependency rules

1. Pages call services and render their results.
2. Services apply rules and coordinate adapters/repositories.
3. The HTTP client handles transport; the adapter handles provider JSON.
4. Repositories use utils/db_connection.py and receive transaction-scoped connections.
5. Models and pure helpers should not import Streamlit or open databases.
6. Network calls occur before write transactions.
7. API endpoints remain unset until a provider/version is selected and verified.

These rules prevent a single page file from becoming responsible for credentials, HTTP, SQL, validation and presentation at once.

## Verification performed

- Parsed every scaffold Python file for syntax without importing third-party dependencies.
- Ran main.py and confirmed it prints scaffold status only.
- Checked the documented module paths exist.
- Checked the SQLite DDL still creates 21 tables in an isolated in-memory database.
- Verified placeholder Python modules contain only documentation, except the explicit entry-point status function.

These are scaffold checks, not application tests or proof of live/API/database functionality. No dependencies were installed and no persistent database was created.

## Phase completion

**What we completed:** created the folder skeleton, package markers, six page placeholders, configuration examples, ignore rules, dependency planning files and root README; explained each location and its implementation phase.

**Files created:** 43 initial scaffold files plus README.md and this guide. The Phase 2 checklist was updated. Existing source files and sql/schema.sql were preserved.

**Concepts learned:** packages and modules, separation of responsibilities, entry points, configuration templates, private runtime files and the distinction between placeholders and functioning features.

**Common mistakes to avoid:** putting secrets in examples, assuming a dependency comment installs a package, placing sample records in a live database, and treating empty page files as completed dashboard features.

**Next phase preview:** Phase 7 breaks implementation into eight milestones, with objectives, files, concepts learned and acceptance outputs. Provider selection and authenticated API verification remain open dependencies. The mentoring prompt requires confirmation before moving to Phase 7.
