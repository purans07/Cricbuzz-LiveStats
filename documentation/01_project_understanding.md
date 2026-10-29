# Phase 1 Project understanding

Cricbuzz LiveStats turns cricket API responses into a searchable, persistent SQL dataset and an interactive Streamlit dashboard. This phase explains the intended product before implementation. It is a design proposal, not a working application.

## Source and learning workflow

The project requirements come from Cricbuzz.docx. The learning sequence comes from Prompt to be used in Claude.docx, also supplied as pasted text. The brief refers to a PDF, but the provided project source is a Word document. Retail_Arcade.html is a retail dashboard reference; its retail features are not cricket requirements. Visual adaptation can be considered during the dashboard phase.

The requested workflow has 18 phases, requires confirmation between phases, and reserves SQL practice for one question at a time, advancing only on NEXT. We will explain concepts before code and finalize the design before producing application code.

## 1 Business problem

Cricket followers, media teams, fantasy analysts, and learners need match updates and historical statistics in one place. Live API responses alone are temporary and awkward to compare. A database stores structured history; SQL answers repeatable questions; the dashboard makes those answers accessible without writing Python.

A typical workflow is: view ongoing matches, inspect a scorecard, compare player statistics, run a saved analysis, and correct a player or match-stat record through a validated form. The assignment also lists prediction-related use cases; a trained prediction model is not an explicit deliverable.

## 2 Project objective

Build a modular Python application that fetches Cricbuzz data, validates it, stores supported records in SQL, and exposes live scores, player rankings, 25 analytical queries, and CRUD forms through Streamlit. A successful submission must run from documented setup steps, protect credentials, and explain where each result comes from.

Live means periodically refreshed API snapshots, subject to provider coverage and request quotas. Display the last successful refresh and distinguish live, cached, and sample data. Historical analytics require historical records; a live match list alone cannot satisfy the advanced questions.

## 3 Expected deliverables

| Deliverable | Completion evidence |
| --- | --- |
| Python source with main.py | Application starts and navigation works |
| Home page | Purpose, tools, instructions, documentation and folder guide |
| Live matches page | Match lists, status, venue and detailed batting/bowling scorecards |
| Top player statistics page | Batting and bowling leaders with clear format and category filters |
| SQL analytics page | All 25 specified questions eventually runnable with tabular results |
| CRUD page | Validated create, read, update and delete for players and match statistics |
| SQL schema and sample data | Reproducible database setup with keys and relationships |
| Requirements | Dependency list verified with the implemented app |
| Documentation | Installation, API credentials, database setup and usage |
| Working demonstration | All four functional modules exercised through the dashboard |
| Recording | User-recorded walkthrough showing the completed project |

Settings is an additional page requested by the learning prompt. Interview preparation follows completion and includes 50 questions with answers. Deployment guidance is part of the learning workflow; no hosting provider has been selected yet.

## 4 Technologies and their purpose

| Technology | Why it exists in this project |
| --- | --- |
| Python | Fetch, validate, transform and coordinate data |
| REST and JSON | Exchange structured data with the provider |
| Streamlit | Build the web interface in Python |
| SQL | Persist related records and calculate analytics |
| SQLite initially | Proposed local learning database with minimal setup |
| SQLAlchemy | Centralize connections and provide database dialect support |
| PostgreSQL or MySQL | Alternative database targets if required for deployment |
| Git | Track implementation milestones and recover changes |

Database portability must be tested. SQLAlchemy supports database dialects, but handwritten SQL date functions, standard deviation and some advanced analytics still need dialect-specific treatment. Do not promise identical SQL across all three engines.

## 5 Python libraries

Proposed application dependencies: streamlit for interface and state; requests for HTTP; pandas for tabular transformations and display; SQLAlchemy for database access; plotly for interactive charts. Test dependency: pytest. Optional python-dotenv supports local environment loading if chosen; Streamlit secrets or environment variables can supply configuration without it. Database drivers depend on the chosen engine. Python standard-library modules cover logging, JSON, dates, paths and local SQLite support.

Dependency versions will be selected and checked at environment setup, rather than inventing a requirements file before the design is approved.

## 6 API requirements

We need provider capabilities for live/recent matches, match details and scorecards, players and batting/bowling statistics, series, teams and venues. These are required data capabilities, not verified endpoint paths.

The exact Cricbuzz API provider, subscription, authentication headers, endpoints, quotas, pagination and historical coverage remain to be verified in Phase 5 against the selected provider documentation. Do not assume a RapidAPI subscription or fabricate an API key. Configure credentials outside source control.

For each API capability, later record the method, URL, parameters, sample response, pagination behavior, source identifiers and destination entities. Use explicit connection/read timeouts, bounded retries where appropriate and useful messages for authentication, quota and network failures. Save fixture responses without secrets for repeatable tests.

## 7 SQL knowledge to learn

Beginner questions 1–8 teach SELECT, WHERE, ordering, aggregation, grouping and joins. Intermediate questions 9–16 add conditional aggregation, multi-table joins, distinct match counts and per-player/per-venue summaries. Advanced questions 17–25 add CTEs, window functions, ranking, rolling form, standard deviation and quarterly comparisons.

Supporting database concepts include primary/foreign keys, normalization, constraints, indexes, transactions, parameterized statements, NULL handling and query plans. A transaction makes a group of changes succeed or fail together; parameters keep form values separate from SQL syntax.

We will solve none of the 25 questions in this phase. During Phase 11, each question receives its own business explanation, query logic, SQL, line-by-line explanation, execution-plan discussion and optimization review.

## 8 Streamlit components

Proposed components: page navigation; sidebar filters; select boxes for format, team and player; dataframes for results; metrics for headline statistics; charts for comparisons; forms for CRUD; buttons for refresh and submission; status/error messages; and session state for interaction across reruns.

Streamlit reruns application code after interactions. Forms group related edits before submission. Cache data snapshots to control repeated API/database reads; keep shared connection resources separate from cached result data. Invalidate relevant cached results after CRUD changes. Never cache secrets as displayed data.

## 9 Database requirements

Proposed entities include countries, teams, players, team memberships, venues, series, matches, match participants, innings, batting performances, bowling performances, fielding performances and format-level career statistics. Exact entities and keys will be finalized in Phase 4.

Store provider IDs separately from local identifiers where needed to support repeatable imports. Use unique constraints to prevent duplicate ingestion and foreign keys to prevent orphan records. Store timestamps consistently and convert them for display. Index common date, player, team, match and format lookups based on query plans.

Important cricket details:

- Store legal balls as integers. The scorecard value 4.2 overs means 26 balls, not 4.2 decimal overs.
- Batting average is runs divided by dismissals; an average of averages is usually wrong.
- Strike rate uses runs and balls faced; economy uses runs conceded and legal balls.
- Distinguish innings from matches, especially for Tests.
- Preserve ties, no results, unfinished matches and unknown values.
- Keep career totals separate from incomplete imported match history.
- Questions 13 and 24 define a consecutive-batter combined-score proxy. Do not label that as actual runs scored together unless partnership-event data supports it.
- Advanced questions need enough history: repeated venues, ten-match form, five head-to-head games and at least six eligible quarters.
- Label generated sample data explicitly. Empty analytics results are valid when thresholds are not met.

A custom SQL interface should use read-only access with result limits; CRUD uses separate validated write paths. Public write access requires an authorization decision before deployment.

## 10 Proposed folder structure and module responsibilities

This is the proposed structure; application folders will be created in Phase 6.

```text
project/
  main.py
  config.py
  requirements.txt
  README.md
  .env.example
  .gitignore
  .streamlit/config.toml
  api/
  database/
  models/
  services/
  pages/
  utils/db_connection.py
  sql/schema.sql
  sql/queries/
  data/sample/
  assets/
  images/
  documentation/
  tests/
```

| Module | Responsibility and reason |
| --- | --- |
| main.py | Entry point and navigation; satisfies the brief's named source deliverable |
| config.py | Validate settings centrally so credentials and paths are not scattered |
| api/ | HTTP client, provider response handling and endpoint adapters |
| database/ | Repository operations and schema lifecycle |
| models/ | Shared record definitions and validation contracts |
| services/ | Coordinate imports, CRUD rules and analytical workflows |
| pages/ | Home, Live Matches, Top Players, Analytics, CRUD and Settings views |
| utils/db_connection.py | Single connection entry point explicitly requested by the brief |
| sql/ | Reviewable schema and saved analytical statements |
| data/sample/ | Clearly labeled reproducible sample input |
| assets/ | Shared styling and static interface assets |
| images/ | Documentation screenshots |
| documentation/ | Phase guides, architecture, setup and learning notes |
| tests/ | API, database, service and interface checks |
| requirements.txt | Reproducible application dependencies |
| .env.example and .gitignore | Document setting names and exclude real credentials/local outputs |

Typical flow: API → validation and transformation → repositories → SQL database → analytics/services → Streamlit. CRUD forms go through validation and services before database writes. Detailed architecture and ER diagrams belong to Phases 3 and 4.

## 11 Development roadmap

| Phase | Outcome |
| --- | --- |
| 1 Understanding | Agreed purpose, deliverables and learning plan |
| 2 Requirements | Mandatory, optional, bonus and future checklist |
| 3 System design | Layer boundaries, data flow and architecture diagram |
| 4 Database design | Normalized schema, ER diagram, constraints and DDL |
| 5 API analysis | Verified provider contract and field mappings |
| 6 Structure | Create the approved project skeleton |
| 7 Implementation plan | File-level milestones and acceptance criteria |
| 8 Database implementation | Working schema, indexes, views and sample data; complete before API implementation |
| 9 API implementation | Resilient retrieval and repeatable ingestion |
| 10 CRUD | Validated transactional player and match-stat operations |
| 11 SQL analytics | Work through questions 1–25 individually using NEXT |
| 12 Streamlit | Build and explain one page at a time |
| 13 Visualization | Add charts tied to useful analytical questions |
| 14 Error handling | Review failures consistently across layers |
| 15 Testing | Unit, integration, database, API and interface validation |
| 16 Deployment | Select a host and document configuration and persistence |
| 17 Documentation | Final setup guide, screenshots and walkthrough notes |
| 18 Interview preparation | 50 questions and detailed answers |

Error handling, tests and notes should accompany implementation; their later phases consolidate coverage rather than postponing basic quality.

## 12 Fourteen-day timeline

This is an effort estimate beginning on your chosen start date, not an asserted assignment deadline. Confirmation pauses and one-query-at-a-time learning can extend elapsed time.

| Day | Planned work |
| --- | --- |
| 1 | Phases 1–2, understanding and requirements |
| 2 | Phases 3–4, architecture and database design |
| 3 | Phases 5–7, API verification, structure and milestones |
| 4–5 | Phase 8, database implementation and checks |
| 6–7 | Phase 9, API client and ingestion |
| 8 | Phase 10, CRUD validation and transactions |
| 9–10 | Phase 11, 25 SQL lessons at the learner's pace |
| 11–12 | Phases 12–13, pages and visualizations |
| 13 | Phases 14–16, failure review, testing and deployment preparation |
| 14 | Phases 17–18, documentation, demo recording and interview preparation |

The SQL lessons are the largest learning-time uncertainty. API access and sufficient historical coverage are the largest data dependencies. Verify coverage before promising advanced analytics on real data.

## Common mistakes to avoid

Do not put every operation in main.py, hardcode credentials, concatenate form values into SQL, repeatedly fetch on every rerun, insert duplicate matches on refresh, treat missing values as zeros, or show sample records as current live scores. Validate one complete data path before expanding the interface.

## Phase completion

Completed: reviewed the supplied project brief and mentoring prompt; explained the business objective, expected outputs, stack, library roles, API needs, SQL skills, UI components, database needs, proposed modules, roadmap and timeline.

File created: documentation/01_project_understanding.md.

Concepts introduced: REST/JSON, persistence, separation of responsibilities, database relationships, transactions, caching, cricket statistical grain and data coverage.

Next phase: extract and categorize the requirements into a traceable checklist. Phase 2 and application implementation remain pending your confirmation, as requested by the supplied learning prompt.

## Technical reference links

- Streamlit multipage apps: https://docs.streamlit.io/develop/tutorials/multipage
- Streamlit caching: https://docs.streamlit.io/develop/concepts/architecture/caching
- SQLAlchemy engine configuration and dialects: https://docs.sqlalchemy.org/en/21/core/engines.html
- Requests timeouts: https://requests.readthedocs.io/en/stable/user/advanced/
