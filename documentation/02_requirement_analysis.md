# Phase 2 Requirement analysis

> Current status (2026-10-29): PostgreSQL/MySQL support and fresh quota/history verification are completed within the tested scope. See [remaining requirements completion](remaining_requirements_completion.md). Older phase checkpoints below are historical; the assignment deadline remains unverified.

This checklist defines what Cricbuzz LiveStats must deliver and how completion will be demonstrated. It covers the project brief and the mentoring workflow without implementing features or solving SQL questions.

## Sources and status conventions

**B** means an explicit requirement in Cricbuzz.docx. **P** means an explicit instruction in Prompt to be used in Claude.docx. **D** means a proposed engineering decision needed to make a requirement reliable or measurable. Optional, bonus and future items below are suggestions, not additional assignment obligations. Retail_Arcade.html supplies no mandatory cricket functionality.

A checked box means the stated activity is complete and has evidence. An unchecked box means it is pending. Identifying a requirement does not mean its feature is implemented. All application requirements remain pending at this stage.

- [x] Read both source documents and identify the product scope (Phase 1 guide).
- [x] Extract and classify functional, quality, delivery and learning requirements (this file).
- [x] Inventory all 25 SQL questions without solving them (this file).
- [x] Finalize architecture in Phase 3 (documentation/03_system_design.md).
- [x] Finalize the schema in Phase 4 (documentation/04_database_design.md and sql/schema.sql).
- [x] Complete Phase 5 API documentation analysis (documentation/05_api_analysis.md).
- [x] Select provider/version and verify authenticated responses. Historical coverage and current account quota remain limited/unverified; see the dated audit.

Current acceptance is summarized in [the 2026-10-29 audit](requirements_audit.md). Checked items describe implemented/observed scope, not global data completeness. DB-02 is accepted on the tested engines; API-04 has dated quota and broader observed history evidence; DEL-10 is unverified because the assignment date is unknown.

## Mandatory product requirements

These are the submission baseline. Acceptance evidence will be produced during implementation and testing.

### Data integration

- [x] **API-01 [B]** Use the Cricbuzz cricket REST API through Python requests. Evidence: a successful authenticated request to the selected provider, with credentials excluded from source and logs.
- [x] **API-02 [B]** Retrieve ongoing match data, detailed scorecards, player statistics and series information. Evidence: provider responses mapped into application records and displayed where relevant.
- [x] **API-03 [B]** Handle API failures. Evidence: useful user messages for network, authentication, quota and malformed-response errors without crashing the page.
- [x] **API-04 [D]** Verify provider endpoints, headers, request limits, pagination and historical coverage in Phase 5. Evidence: reviewed contract and response fixtures exist; current subscription quota and complete historical coverage are not established.
- [x] **API-05 [D]** Use explicit timeouts and bounded retries for appropriate transient failures. Evidence: simulated failure checks terminate predictably and respect provider retry guidance.
- [x] **API-06 [D]** Validate and import records repeatably. Evidence: importing the same snapshot twice does not duplicate matches or performance records.
- [x] **API-07 [D]** Distinguish live, cached and sample data, with last successful refresh time. Evidence: accurate source/status labels and a usable empty or stale state.

### SQL persistence

- [x] **DB-01 [B]** Persist cricket data in a relational SQL database. Evidence: records remain available after restarting the application.
- [x] **DB-02 [B]** Use a database-agnostic design accommodating SQLite, PostgreSQL and MySQL. Evidence: centralized engine configuration, documented dialect differences and an explicit compatibility verification matrix. One engine working is not evidence that all three work.
- [x] **DB-03 [B]** Centralize connection handling in utils/db_connection.py. Evidence: application modules use that entry point rather than scattering connection setup.
- [x] **DB-04 [B]** Deliver SQL table definitions and sample data. Evidence: a clean database can be recreated using documented steps.
- [x] **DB-05 [B/P]** Define primary keys, foreign keys, constraints, relationships and useful indexes. Evidence: invalid relationships are rejected and important access paths are reviewed.
- [x] **DB-06 [B]** Optimize frequently used analytical queries. Evidence: representative query plans and documented indexing decisions; performance targets await a known dataset size.
- [x] **DB-07 [B/D]** Handle NULL and invalid data explicitly. Evidence: unknown statistics stay distinguishable from genuine zero values and failed writes roll back.
- [x] **DB-08 [D]** Preserve innings, dismissals, legal balls, player-team membership and format correctly. Evidence: Test innings are distinct, overs convert correctly, and averages use appropriate denominators.
- [x] **DB-09 [D]** Document historical coverage and provenance. Evidence: API aggregates, imported match history and synthetic samples are identifiable and never combined into misleading totals.

### Streamlit dashboard

- [x] **UI-01 [B]** Provide a multi-page Streamlit application. Evidence: every required page is accessible from consistent navigation.
- [x] **UI-02 [B]** Home shows the purpose, tools, usage instructions, navigation, documentation link and folder guide.
- [x] **UI-03 [B]** Live Matches shows ongoing matches, status, venue, detailed scorecards and batsman/bowler information from the API. Evidence: a valid fixture and a live response exercise the page; no ongoing match produces a clear empty state.
- [x] **UI-04 [B]** Top Players shows API-backed batting and bowling leaders, including most runs, highest scores and most wickets, with clear visualizations.
- [x] **UI-05 [B]** Analytics exposes the 25 specified SQL questions with tabular results. Evidence: each question can be selected and run with its meaning and data scope visible.
- [x] **UI-06 [B]** Provide a custom SQL query interface in addition to saved queries. **D acceptance:** read-only database access, bounded output and useful errors; writes belong in CRUD forms.
- [x] **UI-07 [B]** Provide administrative, form-based CRUD for players and match statistics. Evidence: valid changes persist and are reflected in subsequent reads.
- [x] **UI-08 [D]** Prevent avoidable repeat requests on interface reruns, and refresh relevant results after writes. Evidence: navigation does not cause uncontrolled fetching and CRUD results do not remain stale.

### CRUD behavior

- [x] **CRUD-01 [B/P]** Create player and match-stat records with required-field and relationship validation.
- [x] **CRUD-02 [B/P]** Read existing player and match-stat records through the interface.
- [x] **CRUD-03 [B/P]** Update a selected existing record without changing unrelated records.
- [x] **CRUD-04 [B/P]** Delete a selected record with intentional confirmation and a documented dependent-record policy.
- [x] **CRUD-05 [P/D]** Use transactions and parameterized operations. Evidence: invalid or partial multi-record changes roll back; user values are not concatenated into SQL.
- [x] **CRUD-06 [P/D]** Explain validation, missing-record and database errors clearly. Evidence: invalid inputs leave stored data unchanged.

The brief requires CRUD on match statistics as well as players. CRUD restricted to player names alone does not satisfy the assignment. Deleting whole matches is not explicitly required and depends on the later schema and dependency policy.

### Quality and submission

- [x] **DEL-01 [B]** Deliver complete modular Python source with main.py as the entry point.
- [x] **DEL-02 [B]** Provide a dependency list including Streamlit, database connectivity, requests and pandas.
- [x] **DEL-03 [B]** Follow PEP 8, separate responsibilities, and include useful function docstrings and comments.
- [x] **DEL-04 [B]** Secure API keys and database credentials. Evidence: external configuration and ignored secret files; examples contain placeholders only.
- [x] **DEL-05 [B]** Handle database and API exceptions without exposing secrets or raw internal errors to users.
- [x] **DEL-06 [B]** Use Git for version tracking. Evidence: meaningful local history; remote publication is not needed for this requirement.
- [x] **DEL-07 [B]** Provide setup instructions covering installation, API configuration, database setup and startup.
- [x] **DEL-08 [B]** Demonstrate all four functional modules: live scores, top players, analytics and CRUD.
- [x] **DEL-09 [B]** Supply a project walkthrough recording. Evidence: documentation/demo/cricbuzz-walkthrough.mp4; silent browser capture using a disposable synthetic database, with setup and chapter notes in documentation/demo/README.md.
- [ ] **DEL-10 [B]** Plan submission within 14 days of assignment. The assignment start date is unknown; do not invent a calendar deadline.

## Mandatory SQL question inventory

All original 25 questions are implemented and tested; Q26 adds a saved coverage summary. The following descriptions retain the original acceptance requirements. Dates such as 2024, 2020 and 2022 are fixed by the brief; relative windows use a documented analysis date.

| Status / ID | Required result and eligibility | Minimum data needed |
| --- | --- | --- |
| [x] Q01 | India players: full name, role, batting style, bowling style | Player identity and representation |
| [x] Q02 | Matches played in the last 30 days: description, both teams, venue, city, date; newest first | Match dates, teams and venues |
| [x] Q03 | Top 10 ODI run scorers: name, total runs, batting average, centuries; runs descending | ODI career batting totals and dismissals or authoritative averages |
| [x] Q04 | Venues with capacity strictly above 50,000: name, city, country, capacity; largest first | Venue capacity and location |
| [x] Q05 | Each team's win count; most wins first | Teams and completed match winners |
| [x] Q06 | Player count per playing role | Player roles |
| [x] Q07 | Highest individual score in Test, ODI and T20I | Format and individual batting scores |
| [x] Q08 | Series starting in 2024: name, host country, match type, start date, planned match count | Series metadata |
| [x] Q09 | All-rounders with more than 1,000 career runs AND more than 50 career wickets: name, runs, wickets, format | Format-level career batting and bowling stats, role |
| [x] Q10 | Last 20 completed matches: description, teams, winner, margin, victory type, venue; newest first | Status, completion date, result and venue |
| [x] Q11 | Players in at least two formats: Test, ODI and T20I runs and overall batting average | Format participation, runs and dismissals |
| [x] Q12 | International team wins at home versus away using venue country = team country | International-team classification, countries, winners |
| [x] Q13 | Consecutive batting positions in the same innings with combined runs at least 100: two names, combined runs, innings | Batting positions and innings scores |
| [x] Q14 | Bowlers with at least three qualifying matches at a venue, at least four overs in each: average economy, wickets, match count | Venue, match, bowling balls, runs conceded, wickets |
| [x] Q15 | Matches won by fewer than 50 runs OR fewer than five wickets: player average runs, close-match count and team wins when they batted | Typed margin, batting records and team at match time |
| [x] Q16 | Since 2020, per-player yearly average runs per match and average strike rate; at least five matches in the year | Match dates, batting runs, balls and participation |
| [x] Q17 | Toss-winner match-win percentage grouped by decision to bat or bowl | Toss winner, decision and match winner |
| [x] Q18 | ODI/T20 economical bowlers: overall economy and wickets; at least 10 bowling matches and average at least two overs per match | Format, bowling appearances, balls, runs, wickets |
| [x] Q19 | Average and standard deviation of batting runs since 2022, only innings with at least 10 balls faced; lower deviation is more consistent | Dated batting innings with balls and runs |
| [x] Q20 | Per-player Test, ODI and T20 match counts and batting averages; at least 20 matches overall | Match participation by format, runs and dismissals |
| [x] Q21 | Weighted batting + bowling + fielding score; rank within format using the supplied weights | Runs, average, strike rate, wickets, bowling average, economy, catches, stumpings |
| [x] Q22 | Team pairs with at least five head-to-head matches in the last three years: match counts, both win totals, win margins, batting/bowling-first performance by venue and win percentages | Dated fixtures, teams, winners, typed margins, venue and actual innings order |
| [x] Q23 | Last 10 batting performances: last-five versus last-ten average, strike-rate trends, count of scores above 50, deviation-based consistency, and Excellent/Good/Average/Poor Form labels | Ordered batting performances, dates, runs and balls |
| [x] Q24 | Consecutive-position pairs with at least five occurrences: mean combined runs, count above 50, highest combined score, success percentage and ranking | Player pairs, innings, batting positions and runs |
| [x] Q25 | Quarterly mean runs and strike rate, previous-quarter comparisons, improvement/decline/stability and career phase; at least six quarters and at least three matches per quarter | Multi-year dated performances and distinct match participation |

### Analytical definitions to finalize before implementation

These decisions are resolved in the individual SQL lessons; the list below preserves the design questions that those lessons address. Review the dated requirements audit for current acceptance and limitations.

- **Formats:** establish whether T20 means T20I alone or includes domestic/franchise matches for Q18 and Q20. Other questions explicitly name T20I.
- **Time boundaries:** define the analysis date, timezone, inclusive boundaries and deterministic ordering of same-date performances.
- **Batting averages:** compute aggregated runs divided by dismissals when combining scopes; define zero-dismissal output. Distinguish runs per match from runs per innings.
- **Q13/Q24:** the brief uses consecutive batting positions and combined individual scores. This is a proxy, not actual partnership runs scored while both players were at the crease.
- **Q14:** decide how multiple bowling innings in one Test match contribute to the four-over filter and venue average economy.
- **Q15/Q16/Q20:** define whether participation means selection in the playing XI or an observed batting appearance, and aggregate multiple Test innings before calculating per-match runs. Q15 wins are associated with the player's team in that match.
- **Q17:** define how ties, no-results and matches without a recorded toss affect the denominator.
- **Q18:** define eligible bowling appearances and compute overall economy from total runs and balls, rather than an unweighted average of innings economy.
- **Q19/Q23:** choose population or sample standard deviation and define insufficient-sample behavior.
- **Q21:** preserve the specified weights: batting = runs × 0.01 + batting average × 0.5 + strike rate × 0.3; bowling = wickets × 2 + (50 − bowling average) × 0.5 + (6 − economy) × 2; fielding = catches × 3 + stumpings × 5. The source contains one unmatched closing parenthesis; this transcription balances it without changing the weights. Define missing/non-bowler statistics and tied ranks.
- **Q22:** keep run margins and wicket margins separate; never average their raw numbers together. Use actual innings order rather than assuming toss decision determines who batted first. This is descriptive head-to-head analysis, not a trained prediction model.
- **Q23:** preserve the strict above-50 threshold. Form-label thresholds and the consistency-score formula are unspecified and must be documented before use; also decide how fewer than 10 performances are treated.
- **Q24:** use the same consecutive-position interpretation as Q13; define a good partnership for the success rate, provisionally combined runs above 50 to align with its requested count.
- **Q25:** define whether six quarters must be consecutive, handle gaps, define stable/change thresholds, choose the career-trajectory period, and specify the rule producing Career Ascending, Career Declining or Career Stable.
- **Query count:** the page description says 25+ queries while the explicit SQL deliverable lists 25. The baseline covers all 25 specified questions; an additional saved query can satisfy a strict interpretation of 25+ after the core is complete.

## Mandatory mentoring and process requirements

These come from the adopted mentoring prompt. They are separate from product acceptance.

- [x] **LEARN-01 [P]** Complete Phase 1 understanding before requirements analysis.
- [x] **LEARN-02 [P]** Complete Phase 2 classification and completion checklist.
- [x] **LEARN-03 [P]** Explain frontend, backend, database, API, analytics, utilities, configuration, authentication if needed, and data flow with a text architecture diagram in Phase 3.
- [x] **LEARN-04 [P]** Produce entities, normalized tables, relationships, ER diagram, keys, indexes, constraints and CREATE TABLE statements in Phase 4.
- [ ] **LEARN-05 [P]** Verify API methods, endpoints, auth, headers, quotas, JSON and table mappings in Phase 5.
- [x] **LEARN-06 [P]** Create and explain the approved folder structure in Phase 6.
- [x] **LEARN-07 [P]** Define eight implementation milestones with objectives, files, concepts and expected outputs in Phase 7.
- [x] **LEARN-08 [P]** Complete database implementation, relationships, indexes, views and stored query definitions before moving to API implementation.
- [x] **LEARN-09 [P]** Teach requests, fetching, supported pagination, error handling, retry, JSON parsing and ingestion in Phase 9. Explicitly document if an endpoint has no pagination.
- [x] **LEARN-10 [P]** Teach CRUD validation, errors and transactions in Phase 10.
- [x] **LEARN-11 [P]** Solve Q01–Q25 individually in Phase 11; wait for NEXT between questions. Explain the business problem, concepts, tables, relationships, logic, execution plan, every SQL line and optimization.
- [x] **LEARN-12 [P]** Build Home, Live Matches, Top Players, Analytics, CRUD and Settings one page at a time. Explain purpose, components, inputs, outputs, backend logic and database calls.
- [x] **LEARN-13 [P]** Discuss bar, line, pie, scatter, heatmap, trend, player and venue comparisons and explain suitability in Phase 13. Discussion does not require forcing every chart type onto the dashboard.
- [x] **LEARN-14 [P]** Explain database, API, connection, JSON, validation and Streamlit errors and best practices.
- [x] **LEARN-15 [P]** Explain unit, integration, database, API and UI testing, and supply meaningful sample test cases.
- [x] **LEARN-16 [P]** Explain Streamlit Community Cloud, Render, Railway, Azure, AWS and Docker deployment options and generate steps for the selected approach. A paid account or deployment to all providers is not required.
- [x] **LEARN-17 [P]** Finish README, installation, folders, API setup, database setup, screenshots section and future improvements.
- [x] **LEARN-18 [P]** After completion, provide 50 detailed interview/viva questions and answers covering SQL, Python, Streamlit, APIs and system design.
- [ ] **LEARN-19 [P]** Throughout later phases, explain before coding, use clean modular architecture and appropriate object-oriented design, teach common mistakes, and end every phase with completed work, files, concepts and next-phase preview.
- [ ] **LEARN-20 [P]** Continue respecting confirmation between phases and finalize design before production application code. This is an ongoing workflow requirement, not an implemented feature.

## Optional features

These suggestions may improve usability after the baseline is secure. None is explicitly mandatory in the project brief.

- [x] **OPT-01 [D]** CSV export of analytical results through the native Streamlit table toolbar.
- [ ] **OPT-02 [D]** Search, filters and pagination beyond what is needed to operate required pages.
- [ ] **OPT-03 [D]** Configurable automatic refresh within verified API quotas; a manual refresh can provide the initial update workflow.
- [x] **OPT-04 [D]** Rich player and venue comparison charts beyond the required statistics visuals.
- [x] **OPT-05 [D]** Adapt Retail Arcade colors and layout after agreeing a cricket-specific visual direction.

## Bonus features

These are proposed enhancements, not items labeled bonus by the assignment.

- [x] **BON-01 [D]** An additional saved analytical question beyond the 25 specified, addressing the 25+ wording if needed.
- [ ] **BON-02 [D]** Automated checks on each Git change through a CI workflow.
- [ ] **BON-03 [D]** CRUD audit trail with before/after values and timestamps.
- [ ] **BON-04 [D]** Visible automated compatibility checks for all three database engines, beyond documenting the portability boundary.

Database-agnostic design remains mandatory; the bonus is an automated compatibility suite, not permission to ignore portability.

## Future improvements

- [ ] **FUT-01 [D]** Trained match predictions with explicit evaluation and uncertainty, separate from descriptive Q22 output.
- [ ] **FUT-02 [D]** Ball-by-ball ingestion and actual partnership-event analytics.
- [ ] **FUT-03 [D]** Scheduled ingestion, historical backfill and monitoring at larger scale.
- [ ] **FUT-04 [D]** Multi-user roles and authentication for a publicly hosted administrative interface. If public write access is chosen during deployment, access control becomes a prerequisite for that deployment.
- [ ] **FUT-05 [D]** Alerts, favorites or fantasy-team assistance beyond the analytics assignment.

## Dependencies and acceptance boundaries

| Dependency or uncertainty | Effect | Resolution point |
| --- | --- | --- |
| Provider and credentials not selected | Live retrieval cannot yet be validated | Phase 5 API analysis |
| Historical access unknown | Advanced query thresholds may have no eligible real records | Phase 5 coverage map; labeled sample fixtures for tests |
| Career stats and match history may cover different periods | Aggregates cannot be silently mixed | Phases 4–5 provenance design |
| Country mapping and venue capacity may be missing | Q04/Q12 require explicit unknown-data handling | Phases 4–5 field coverage |
| Ranking and form definitions incomplete | Q21/Q23/Q25 outputs could vary by hidden assumptions | Individual SQL lesson before implementation |
| Primary database and compatibility scope pending | Setup and advanced SQL syntax depend on engine | Phases 3–4 |
| Deployment target and persistence pending | Local file storage may not meet hosted durability needs | Phase 16, with architecture provisions in Phase 3 |
| Assignment date unknown | No exact submission date can be calculated | User-provided assignment date when available |

An empty query result can be correct when no rows satisfy its thresholds. Query correctness must still be demonstrated with known fixtures and expected results. A synthetic demo does not count as verified live API integration. Meeting a query's thresholds must never involve inventing real player records.

## Completion overview

| Area | Current status | Evidence required to mark complete |
| --- | --- | --- |
| Understanding | Complete | Phase 1 guide |
| Requirements analysis | Complete | This categorized checklist and SQL inventory |
| Architecture | Complete | Phase 3 system design guide |
| Database design | Complete | Phase 4 design, ER diagram and validated SQLite DDL |
| API integration | Provider-neutral client/ingestion implemented and fixture-tested; provider selection, vendor parser and authenticated verification pending | Phase 9 progress and validation reports; live acceptance still open |
| Database | Local SQLite complete; other engines unverified | Phase 8 implementation, setup guides and 64 passing checks |
| CRUD | Pending | Validated player and match-stat workflows |
| Dashboard | Pending | Required pages and navigation |
| SQL analytics | Pending, 0 of 25 implemented | Individual queries and correctness evidence |
| Deployment | Pending workflow phase | Selected deployment instructions and validation if deployed |
| Documentation | Complete | Current operational guides and Phase 17 handoff |
| Recording | Pending | Playable walkthrough |
| Interview preparation | Complete | 50 answered questions in Phase 18 |

## Phase completion

**What we completed:** extracted and classified the source requirements, defined acceptance evidence, inventoried all 25 SQL questions, and recorded data dependencies and unresolved analytical definitions.

**File created:** documentation/02_requirement_analysis.md.

**Concepts learned:** mandatory scope versus enhancements; requirement traceability; acceptance criteria; implementation status versus analysis completion; and why data coverage and statistical definitions affect correctness.

**Common mistakes:** treating every suggested feature as compulsory, marking features done after writing a plan, confusing live data with historical coverage, dropping SQL thresholds, and omitting match-stat CRUD.

**Next phase preview:** Phase 3 designs the frontend, backend, database, API, analytics, utility and configuration layers, considers authentication needs, and provides data flows and a text architecture diagram.

Status update after Phase 3: architecture is documented in 03_system_design.md. Phase 4 is complete with validated design DDL; Phase 5 documentation analysis is complete. Provider selection and authenticated verification remain pending; Phase 6 folder structure is complete. Phase 7 implementation planning is complete. Phase 8 local environment/database implementation is complete; API/provider verification remains pending. Phase 9 provider-neutral work is implemented; provider selection, vendor mapping and live verification remain pending before Phase 10.

## Phase 8 evidence update

Checked DB items refer to the implemented local SQLite baseline, not PostgreSQL/MySQL compatibility or verified real-data ingestion. See documentation/08_database_implementation.md and documentation/08_validation_report.md. Full CRUD services, live API functionality, analytical questions and dashboard pages remain pending. The local Phase 8 implementation checkpoint records the source and guides; original reference documents remain untouched and untracked.

## Phase 9 evidence update

HTTP transport, explicit pagination support, normalized snapshot validation, transactional imports and manual-edit protection are implemented with synthetic tests. The combined suite passes 136 checks. See documentation/09_api_implementation.md and documentation/09_validation_report.md. API requirements and LEARN-09 remain open because no selected provider adapter or authenticated live responses have been verified. Database schema 2 adds durable import metadata without modifying the existing Phase 8 sample file.

## User-captured v2 match-list update

Provider selection is now RapidAPI cricketapilive/cricbuzz-cricket v2, established from the user's screenshots. A supplied HTTP-200 body has a tested match-list adapter and temporary database round trip; the combined suite passes 159 tests. See documentation/09_captured_match_list.md. Full request URL/host, scorecard/player mappings and local authenticated verification remain pending; API milestone acceptance is still open.

## Authenticated live-match update

On 22 October 2026, the configured API returned HTTP 200 (not marked as gateway mock) and imported four matches and 12 innings into the separate live database. The combined suite passes 164 checks. Live-match integration is complete, while the overall API milestone remains pending detailed scorecard/player/career and series coverage. See documentation/09_live_verification.md.

## Phase 9 final status

API integration milestone M3 and LEARN-09 are complete. Authenticated provider checks, player/profile career ingestion, duplicate replay, rollback and source handling have evidence in 09_api_implementation.md and 09_phase_completion_result.json (188 tests). Product-level dataset completeness, historical depth, fielding totals, UI labels and later phases remain open; earlier progress paragraphs are historical checkpoints.

## Phase 10 final status

M4 service implementation and LEARN-10 are complete (218 tests, including 30 new CRUD tests). CRUD-01/03/04 have implemented service behavior; final product acceptance remains open until the Phase 12 interface and delete confirmations exist. CRUD-02 explicitly requires the interface and remains open. See 10_crud_guide.md for validation, soft-delete dependencies, ownership, restore/release and version checks. The working databases were not edited during verification.

## Phase 11: Question 1

Q01 is implemented and explained in 11_q01_india_players.md, with bound-date SQL, actual SQLite query plans and four passing boundary tests. The sample returns six fictional profiles. Live membership coverage is absent and returns no rows. Q02–Q25 and final LEARN-11 acceptance remain pending; advance only on NEXT.

## Phase 11: Question 2

Q02 is complete: rolling UTC start-time bounds, both participant slots, optional venue and explicit played-status policy. Actual results/plans are in 11_q02_result.json and line-by-line explanation in 11_q02_recent_matches.md. Q03–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 3

Q03 is complete: latest committed ODI career snapshots from one bound source, defined average handling, stable top-ten order and six boundary tests. Lesson: 11_q03_top_odi_run_scorers.md; measured outputs/plans: 11_q03_result.json. The live population has one eligible career player and is not a global ranking. Q04–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 4

Q04 is complete: strict capacity > 50,000, optional country join, stable descending order and four boundary tests. Lesson: 11_q04_large_venues.md; results/plans: 11_q04_result.json. Live venue capacities remain unknown. Q05–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 5

Q05 is complete: confirmed completed match wins per team, including zero-win teams, with correct match grain and five boundary tests. Lesson: 11_q05_team_wins.md; actual outputs/plans: 11_q05_result.json. Live winner/result enrichment remains incomplete. Q06–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 6

Q06 is complete: active players counted per defined role, including zero-player roles, with five focused tests. Unknown roles are inventoried separately; 21 of 22 live profiles are currently unassigned. Lesson: 11_q06_players_per_role.md; results/plans: 11_q06_result.json. Q07–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 7

Q07 is complete: per-format MAX of latest individual career highest scores from one selected source. Missing requested formats remain NULL; ambiguous T20 is not relabeled T20I. Five focused tests pass. Lesson: 11_q07_highest_score_per_format.md; actual results/plans: 11_q07_result.json. Live values are not worldwide records. Q08–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 8

Q08 is complete: series starting in 2024, one display row per identity with independent host/format lists and preserved planned totals. Five focused tests pass. Lesson: 11_q08_series_started_2024.md; actual results/plans: 11_q08_result.json. Live 2024 historical coverage remains unimported. Beginner Q01–Q08 are complete; Q09–Q25 remain pending, advancing only on NEXT.

## Phase 11: Question 9

Q09 is complete: canonical all-rounders exceeding both strict career thresholds in the same format, using latest snapshots from one source. Five focused tests pass. Lesson: 11_q09_qualified_all_rounders.md; actual results/plans: 11_q09_result.json. Live profile/career coverage remains limited. Q10–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 10

Q10 is complete: up to twenty completed matches, both team slots, optional winner/venue, separate victory units, and explicit known-completion-first ordering. Six focused tests pass. Lesson: 11_q10_last_completed_matches.md; measured outputs/coverage/plans: 11_q10_result.json. Unknown live completion/result metadata prevents a complete real-world chronology claim. Q11–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 11

Q11 is complete: pivot latest Test/ODI/verified T20I career runs for players with positive appearances in at least two target formats, computing a pooled runs/dismissals average with NULL completeness checks. Six focused tests pass. Lesson: 11_q11_cross_format_batting.md; measured outputs/plans: 11_q11_result.json. Overall scope is the evidenced target formats, not unverified T20/league coverage. Q12–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 12

Q12 is complete: conditional counts of confirmed completed international-team home/away wins by country IDs, with a separate unclassified-win counter and zero-win teams retained. Six focused tests pass. Lesson: 11_q12_home_away_wins.md; outputs/coverage/plans: 11_q12_result.json. Live geography/winner/classification coverage remains limited. Q13–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 13

Q13 is complete: active ordinary-innings batting self-join on same innings and exact position + 1, combined individual scores >= 100. Actual partnership totals are not claimed. Six focused tests pass. Lesson: 11_q13_adjacent_batting_pairs.md; outputs/plans: 11_q13_result.json. Q14–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 14

Q14 is complete: combine ordinary bowling innings into matches, require >=24 known balls in each of at least three venue matches, then report mean match economy, wickets and count with NULL completeness guards. Six focused tests pass. Lesson: 11_q14_bowling_by_venue.md; outputs/coverage/plans: 11_q14_result.json. Live history has only one detailed bowling match. Q15–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 15

Q15 is complete: typed strict close-win margins, per-player match totals before averaging/counting, and wins using the recorded batting team. Six focused tests pass. Lesson: 11_q15_close_match_batting.md; outputs/coverage/plans: 11_q15_result.json. Exceptional performance has no invented cutoff; live qualifying evidence remains incomplete. Q16–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 16

Q16 is complete: UTC start years since 2020, at least five evidenced appearances per player/year, match-level batting aggregation, mean match strike rate and NULL completeness guards. Six focused tests pass. Lesson: 11_q16_yearly_batting.md; outputs/coverage/plans: 11_q16_result.json. Missing batting does not become a fabricated DNB zero. Q17–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 17

Q17 is complete: toss-winner win percentages by bat/bowl decisions over completed resolved-result matches, including nonwinning resolved outcomes in denominators and preserving empty rates as NULL. Six focused tests pass. Lesson: 11_q17_toss_decision_win_rate.md; results/coverage/plans: 11_q17_result.json. Synthetic association is not causal evidence; live metadata remains incomplete. Q18–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 18

Q18 is complete: pooled ODI/T20 economy and wickets after >=10 evidenced bowled matches and >=12 known balls per match on average. Seven focused tests pass. Lesson: 11_q18_limited_overs_economy.md; outputs/coverage/plans: 11_q18_result.json. Live limited-overs bowling coverage is absent. Q19–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 19

Q19 is complete: known individual innings scores since 2022 with >=10 faced balls, descriptive population deviation by centered squared differences, sample-size disclosure and stable ordering. Six focused tests pass. Lesson: 11_q19_batting_consistency.md; outputs/math-runtime/plans: 11_q19_result.json. Live singleton deviations do not establish consistency. Q20–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 20

Q20 is complete: latest selected-source Test/ODI/T20 international career counts and dismissal-based averages, requiring >=20 known target-format matches and rejecting overlapping T20 buckets. Seven focused tests pass. Lesson: 11_q20_format_matches_and_averages.md; outputs/source-code evidence/plans: 11_q20_result.json. Live data covers one enriched career; provider T20 is not asserted to be T20I. Q21–Q25 remain pending; advance only on NEXT.

## Phase 11: Question 21

Q21 is complete: exact supplied batting/bowling/fielding weights over latest selected-source career rows, complete-case inputs and unrounded per-format dense ranks. Eleven focused checks pass. Lesson: 11_q21_weighted_performance_rank.md; outputs/coverage/plans: 11_q21_result.json. Missing live fielding/undefined ratios prevent valid complete scores and are not replaced with zero. Q22–Q25 remain pending; advance only on NEXT.

Q22 is complete: canonical team pairs with five completed matches in explicit three-calendar-year windows; separate typed margins, unknown-result audits and actual first-innings venue breakdowns. Sample one pair; live no qualifying history. Question 23 awaits NEXT.

Q23 is complete: last-five/ten completed batting-match averages, pooled strike-rate comparisons, strict above-50 match counts, population deviation and documented heuristic form categories. Unknown/short histories remain unclassified. Sample 12 players; live no eligible completed batting records. Question 24 awaits NEXT.

Q24 is complete using the explicitly labeled adjacent-position combined-score proxy: canonical player pairs, five appearances, average/highest scores, strict above-50 success rates and dense ranking. Incomplete-score combinations remain visible and unranked. Actual stand data remains unavailable. Sample ten qualifying pairs; live none. Q25 awaits NEXT.

Q25 is complete: twelve completed calendar quarters, six observed quarters with at least three batting matches in every observed quarter, mean runs and mean match strike rates, gap-aware LAG comparisons and documented centered-OLS career phases. Sample 144 rows/12 players; live no eligible history. All Q01–Q25 lessons, SQL, result evidence and validations are complete; LEARN-11 is accepted. Phase 12 has not started.

## Phase 12 — Home page

Home is complete: runnable Streamlit shell, explicit Home-only navigation, sample/provider labels, atomic saved counts/import metadata, roadmap, usage instructions and bundled documentation/folder/setup/SQL guide previews/downloads. Ten isolated service/UI checks pass within 389 total tests; the local sample preview was inspected in the browser. UI-02 is accepted. UI-01 and LEARN-12 remain pending until all six pages are implemented. Live Matches is next; no later page or phase has started.

## Phase 12 — Live Matches page

Live Matches implementation is complete: registered navigation, saved sample/provider selection, status and match filters, venue/status/source timestamps, innings scores and active batting/bowling tables, explicit guarded list/scorecard refreshes, shared 30-second cooldown and safe empty/error/read-only states. Thirteen focused checks verify captured-provider refreshes and actual Streamlit events; no fresh upstream call was made. Saved authenticated provider data was inspected in the browser. UI-03 implementation is delivered; its fresh live-response acceptance remains pending an explicit operator refresh. UI-01/LEARN-12 remain pending until all six pages are ready. The full suite passes 402 tests. Top Players is next.

## Phase 12 — Top Players page

Top Players implementation is complete: source/exact-format latest career rankings, runs/highest-score/wicket and rate measures, match-count filter, dense ties, coverage/import context, profiles and read-only local reload. Eleven focused checks pass within 413 total tests; no new HTTP calls were made. The saved provider dataset has one enriched career player, which is explicitly disclosed. UI-04 visualization/global-coverage acceptance remains pending Phase 13 and wider imports; UI-01 and LEARN-12 remain pending completion of the remaining pages. Analytics is next.

## Phase 12 — Analytics page

Analytics is complete: all 25 saved questions and the Q22 venue variant, inspectable lessons/SQL, named parameter controls, explicit run/results/coverage states, and a local-only custom SQL workspace with read-only connection, restrictive SQLite authorizer, single-statement execution and time/row/value/output budgets. All 26 saved outputs ran on sample/live snapshots. Forty-four new checks pass within 457 total tests. UI-05/UI-06 are accepted; local query limits are not an OS sandbox. UI-01 and LEARN-12 remain pending the CRUD and Settings pages. CRUD is next.

## Phase 12 — CRUD page

CRUD is complete: profile and batting/bowling/fielding forms, relationship-aware creation, loaded version snapshots, stale-edit refusal, confirmed reversible deletion, restore and explicit API override/release. Readonly mode hides forms and existing services enforce access. Thirteen UI/catalog cases run on temporary datasets; no working sample/live edits or API calls occurred. UI-07 is accepted. The suite passes 470 tests. Settings is next; UI-01/LEARN-12 remain pending the final page.

## Phase 12 — Settings and completion

Settings is complete: secret-safe API configuration readiness, read-only database health, trusted access-policy explanation and validated session-only timezone shared across pages. Eight new cases verify diagnostics/privacy/preferences and all six real navigation routes without implicit HTTP or writes. The full suite passes 478 tests. UI-01 and LEARN-12 are accepted: all six page contracts are implemented and documented. Charts, expanded provider history, fresh authenticated dashboard-refresh acceptance and public administrative authentication remain scoped to their milestones; no broader completion is claimed. Phase 13 awaits the next user request.

## Phase 13 — Visualization

Phase 13 is complete: Top Players ranking/player-comparison bars and Analytics quarterly line/heatmap, Q19 scatter and Q14 venue comparisons, with source/format/sample/coverage labels, separate units, stable IDs or distinct result-row labels, missing-value gaps and source tables. Pie suitability is explained without implying a complete imported population. Fourteen new cases pass within 492 tests. UI-04, OPT-04 and LEARN-13 visualization behavior is accepted; one-player live career coverage and wider historical population remain limited. Working files were read only and no API quota was used. Phase 14 awaits NEXT.

## Phase 14 — Error Handling

Phase 14 is complete: specific expected-error paths remain, shared route/application boundaries hide unexpected private details without swallowing rerun/stop/process control flow, allowlisted coded diagnostics cover page/API/CRUD failures, and client key references clear even if HTTP session cleanup fails. Eighteen new cases verify safe recovery, rollback, redaction and control flow within 510 total tests. No working-data mutations or live API failures were induced. LEARN-14 is accepted. Phase 15 awaits NEXT.

## Phase 15 — Testing

Phase 15 is complete: unit/integration/database/API/UI strategy and requirement evidence matrix, two cross-module lifecycle/import/ranking/chart journeys, and a default requests transport guard with a direct regression check. The final JUnit-derived report records 513 passed, zero failures/errors/skips and unchanged working sample/live file fingerprints. Lint, format, whitespace and dependency checks pass. CRUD-01–04, UI-08 and DEL-05 checklist states now reflect existing UI/service/error evidence; LEARN-15 is accepted. No fresh provider/hosted acceptance, coverage percentage, global data completeness or cross-engine verification is claimed. Phase 16 awaits NEXT.

## Phase 16 — Deployment preparation

LEARN-16 is complete: current primary-source comparison of Community Cloud/Render/Railway/Azure/AWS/Docker, selected Docker/readonly sample design, safe sample bootstrap, explicit-copy image/context, Compose and deployment/recovery steps. Six startup cases pass within 519 tests; Compose syntax passes. Docker CLI exists but the engine is stopped, so image build/run and hosted acceptance remain unperformed. No cloud resource, publication, paid service or private-image data was created. Phase 17 documentation is next; runtime acceptance remains explicitly pending.

## Phase 17 — Documentation

DEL-07 and LEARN-17 are complete: current README, installation, folder map, API/database setup, user guide, screenshots section and future improvements. The index preserves historical phase evidence. Screenshot captures/video and Docker/host runtime acceptance remain pending. Phase 18 awaits NEXT.

## Phase 18 — Interview preparation

LEARN-18 is complete: 50 detailed project-specific questions and answers, introduction, evidence links and practice guidance in 18_interview_preparation.md. All requested teaching phases have material. Outstanding screenshot/video, broader real-data coverage and Docker/host runtime acceptance remain open; no new live requests or publication occurred.

## Requirements audit — 2026-10-29

Closed documentation gaps with 107 application function docstrings, added Q26 without changing Q01–Q25, captured all six pages plus charts/mobile, and recorded a silent walkthrough. Readonly integrity checks passed for both working databases; 26 query plans were collected. SQLite-only runtime, current provider quota/complete historical coverage, and the unknown assignment date remain explicitly open. See requirements_audit.md and requirements_audit_evidence.json.
