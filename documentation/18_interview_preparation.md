# Phase 18 — Interview preparation

> Current status (2026-10-29): PostgreSQL/MySQL support and fresh quota/history verification are completed within the tested scope. See [remaining requirements completion](remaining_requirements_completion.md). Older phase checkpoints below are historical; the assignment deadline remains unverified.

These 50 questions and model answers describe the implemented project. Adapt them to your own words and explain only work you understand. Evidence is in the linked guides; do not present sample results as professional cricket facts or planned hosting as a completed deployment.

## A two-minute project introduction

“I built Cricbuzz LiveStats with Python, SQLite, Streamlit and Plotly. It separates fictional training data from imported provider data and provides six dashboard pages, 25 SQL analyses, player comparisons and validated CRUD. I focused on correct fact relationships, source ownership, missing values and safe transactional imports. The checked suite has 519 passing tests. Provider history is currently limited, and deployment packaging is prepared with runtime acceptance still pending. I can demonstrate the sample workflow and explain the tradeoffs behind the SQL and service boundaries.”

## Questions and answers

### 1. How would you introduce this project in an interview?

Cricbuzz LiveStats is a Python, SQLite and Streamlit application that turns saved cricket data into match views, player rankings and 25 SQL analyses. It separates fictional training fixtures from provider imports and includes validated player/statistic CRUD, interactive Plotly charts and safe error handling. I would demonstrate the sample first, then explain the reviewed RapidAPI integration. I would state that provider history is partial and deployment is prepared but has not passed container or hosted runtime acceptance.

### 2. What business problem does the project solve?

Raw API responses are nested and inconvenient for repeated comparisons. The project normalizes supported responses into related tables, records their source and import context, and makes saved results explorable through a dashboard. SQL answers questions about form, consistency, venues and career performance. This supports reproducible learning and analysis; the current small provider dataset does not support claims about all professional players or every historical match.

### 3. Explain the architecture and the responsibility of each layer.

Streamlit page entry points delegate presentation to ui modules. Services implement business rules such as validation, ownership, ranking and ingestion. Database utilities provide controlled transactions, while SQL files describe the schema and analytical questions. Explicit refresh calls the API client and normalizer before transactional ingestion; charts then consume committed saved results. This keeps widget code from becoming the place where HTTP, validation and database writes are mixed together.

### 4. Why separate sample and live databases?

Sample data is deliberately fictional, deterministic and useful for demonstrating questions that require substantial history. Provider data has different provenance and incomplete coverage. Separate files plus a recorded dataset mode prevent training fixtures from silently entering real-data rankings. A configured mode must match the database. The fixed sample analysis date is 2026-10-01, so demonstrations remain reproducible rather than changing with the calendar.

### 5. Why did you choose SQLite, and what are its limits?

SQLite makes local setup straightforward because it uses a file and does not require a database server. It supports the joins, transactions, constraints and window functions needed here. Its write concurrency and file-based operational model require care for a hosted multi-instance writable application. PostgreSQL would be a candidate for that expansion, but SQLAlchemy alone does not prove portability: schema, date expressions, queries, migrations and acceptance tests must also be checked.

### 6. Why use Python services instead of putting all logic in Streamlit pages?

A service can validate an operation and perform it transactionally without knowing which widget initiated it. This makes the same behavior usable from the UI, CLI and tests. For example, an edit must respect expected row version and API ownership regardless of its caller. The presentation layer handles choices and messages, while the service owns the invariant. This separation also makes failures easier to isolate.

### 7. How do configuration and environment variables work?

The application validates dataset mode, SQLite path, timezone and access policy. Optional private .env values are loaded with process-environment overrides, which lets an explicit launch command choose a safe sample target. API settings use a separate reviewed manifest and private key. Configuration is checked before use, rather than accepting arbitrary URLs or guessing endpoints. The current loader does not read Streamlit st.secrets; claiming that it does would misdescribe the implementation.

### 8. What Python practices improve maintainability here?

Small modules, explicit dependencies, validated inputs and context-managed resources keep behavior understandable. The project uses typed/structured configuration and separates pure transformations from I/O where practical. Pure chart builders can be checked without an HTTP server, while database operations receive a controlled database object. I would discuss these concrete boundaries instead of claiming every function is pure or that adding type hints automatically guarantees correctness.

### 9. How should exceptions be handled?

Expected validation, configuration, database and provider failures should produce a useful safe message at the appropriate boundary. Unexpected page failures are caught by a shared Exception boundary that logs an allowlisted code and offers recovery. Raw keys, response bodies, SQL and tracebacks are not shown to visitors. BaseException control flow is not swallowed, preserving Streamlit rerun/stop and process interruption. An action may have committed before rendering fails, so users should inspect saved state before repeating it.

### 10. How do you avoid resource leaks?

Connections and transactions are managed through context managers so success and failure both release resources. The HTTP client closes its session and clears retained key references even if closing the session fails. Transaction cleanup must roll back unsuccessful writes. Clearing an object reference is useful hygiene but is not a promise that every copy of a Python string has been securely erased from memory.

### 11. How did you select and verify the API contract?

The selected provider is RapidAPI cricketapilive/cricbuzz-cricket, listing version v2. A reviewed JSON manifest records its HTTPS host, headers, supported paths and HTTP policy; authenticated capability evidence was captured on 2026-10-22. Listing v2 still uses verified v1 route paths, such as /matches/v1/live. I would distinguish documentation, a successful response and an implemented import adapter: verifying an endpoint does not automatically implement its entire data workflow.

### 12. How is API authentication protected?

The private CRICBUZZ_API_KEY supplies x-rapidapi-key while the manifest supplies the host and non-secret headers. Credentials belong in private environment configuration, never tracked examples, screenshots or logs. A previously shared credential should be replaced through the provider account. The application can verify configuration readiness without sending HTTP, but that check cannot establish that a key is valid or a subscription is active.

### 13. How do you normalize nested match-list JSON?

The adapter walks typeMatches, seriesMatches and supported seriesAdWrapper entries to reach matches. It reads matchInfo and optional matchScore, then maps source identities and related teams, venues, series and innings into normalized records. Advertisement entries are skipped. Missing score details remain absent or NULL, rather than being invented as zeros. Tests should include mixed wrappers, missing optional fields and malformed supported records, not just the happy-path response.

### 14. What does idempotent ingestion mean?

Repeating the same supported import should not create duplicate matches, players or snapshots or unnecessarily change dataset revision. Source-scoped external identities and duplicate detection make repeated responses recognizable. The importer also considers stale data and protects operator overrides and tombstones. Idempotency is broader than using INSERT OR IGNORE: an update can still incorrectly overwrite newer data unless freshness and ownership rules are respected.

### 15. Why make an import atomic?

A scorecard can affect identities, innings and multiple batting/bowling records. Committing only half would create an inconsistent analytical view. The supported import is normalized and written within controlled transactional boundaries so a failure rolls back its database changes. This guarantees the transaction's database effects, not that an external HTTP request or quota consumption can be rolled back. Readers should see a committed import rather than partially updated facts.

### 16. How do you handle latency, rate limits and retries?

The reviewed client policy includes connection/read timeouts, response-size and operation budgets, one attempt and minimum request spacing. Dashboard refresh adds a process-local mutex and at least a 30-second cooldown, including Retry-After handling. One attempt avoids hidden retry multiplication of quota. These safeguards are not a distributed account-wide quota manager; multiple processes would need centralized coordination. A transport timeout is also distinct from a complete job scheduling guarantee.

### 17. How is player enrichment different from match ingestion?

Match ingestion establishes match-specific facts, while career enrichment provides profile and cumulative format-level batting/bowling snapshots. The current sync-player workflow makes three requests for profile, batting and bowling. Career-format capability is available separately. Snapshots retain source and exact format labels so repeated cumulative totals are not added together. Current real-data career enrichment covers one player, so sample comparisons are more complete than live comparisons.

### 18. Why is a missing player statistic different from zero?

Zero records an observed value, such as no wickets in a supplied bowling record; NULL records an unknown or unavailable value. Replacing missing fielding data with zero would unfairly lower a weighted ranking and imply coverage that does not exist. SQL qualification, calculations and charts must respect the distinction. Use COALESCE only when the business definition establishes the default, not as a blanket way to fill every blank.

### 19. Explain the main database relationships.

A series contains matches; each match refers to teams and a venue and contains innings. Player participation and batting, bowling and fielding facts associate players with the relevant match or innings. Career snapshots are a separate cumulative grain with source/format/import context. Foreign keys help prevent orphaned records, while services validate cricket-specific relationships that a simple foreign key cannot express. The ER diagram and schema give the exact implemented cardinalities.

### 20. What is normalization, and where does it help?

Normalization separates distinct entities and facts so a team's name is not independently copied into every batting row. A player identity, a match and an innings performance have different grains and update rules. Keeping them separate reduces update anomalies and makes relationships explicit. Normalization does not remove the need for deliberate analytical views or source metadata; convenient reporting joins should still preserve each fact's grain.

### 21. What is the difference between internal IDs and provider IDs?

Internal IDs identify rows within this database. Provider IDs identify resources in one external source and must be interpreted with that source. A scorecard refresh needs the provider match ID, not an arbitrary local match ID. Source-scoped mappings avoid collisions if a second provider also uses the same number. Displaying a name alone is not a reliable substitute for a stable identity because names can repeat or change.

### 22. How are overs represented correctly?

Cricket overs are a count of legal deliveries, not ordinary decimal quantities. The database stores legal balls as integers and formats them as completed overs plus remaining balls. For example, 10.4 represents 64 legal balls in a six-ball over convention; adding it as decimal 10.4 is incorrect. Provider boundary representations require normalization according to the supported adapter. Overs-to-balls conversion belongs at that boundary, not scattered through SQL and UI arithmetic.

### 23. What do transactions and foreign keys each guarantee?

A transaction groups changes so they commit together or roll back together. Foreign keys enforce specified references between tables when enabled. Neither automatically enforces every business rule: for example, a valid player ID can still belong to the wrong side for a particular fact. The project combines constraints with service validation and explicit write transactions using BEGIN IMMEDIATE. This requests a write transaction early rather than discovering contention only after substantial work.

### 24. How are schema changes managed?

Initialization only creates an unused target and refuses to overwrite an existing database. Migration is an explicit operator action; opening the app never silently upgrades files. The additive version-1-to-2 migration records a consistent no-overwrite backup and applies the change transactionally. Supported readers can handle existing schema 1, while ingestion requires schema 2. Before a production change I would stop writers, verify the intended mode/path and test backup restoration.

### 25. How would you explain soft deletion and API overrides?

Soft deletion marks a record inactive so it can be excluded from normal views while preserving identity and recovery options. Provider-owned facts require explicit operator override before manual modification, and later imports must respect that decision. A tombstone prevents a refresh from silently resurrecting a deliberately deleted fact. Restore and release-override are separate intentions: restoring visibility does not necessarily mean surrendering operator ownership.

### 26. How do you prevent one user overwriting another edit?

The form retains the row version that was loaded, and the service checks the supplied expected version during the write. If the record changed meanwhile, the edit is rejected and the operator reloads it. This is optimistic concurrency control. Database writer serialization alone is insufficient: two sequential writes can both succeed while the second uses stale form contents unless the application also checks the version.

### 27. How do INNER JOIN and LEFT JOIN differ?

INNER JOIN retains only matching rows, useful when the question requires an observed qualifying fact. LEFT JOIN retains every left-side entity and uses NULL for an absent right-side match, useful for coverage or players without statistics. Filtering a right-side column in WHERE can accidentally remove those NULL rows and turn the intended outer join into inner-join behavior. I would choose the join from the business question and inspect missing-coverage cases.

### 28. Why can a join produce inflated totals?

Joining multiple one-to-many fact tables creates combinations: two batting rows joined directly to three bowling rows can produce six rows. Summing either measure then overcounts. Aggregate each fact to the intended common grain before joining, or join through unique keys that establish one-to-one relationships. DISTINCT may hide symptoms while also removing legitimate repeated values, so it is not a general fix for an incorrect join.

### 29. When do you use WHERE versus HAVING?

WHERE filters individual input rows before grouping; HAVING filters resulting groups. To rank qualifying players, I might select a source/format in WHERE, group by player and apply a minimum observed match count in HAVING. The order affects meaning and performance. A threshold on an aggregate belongs after aggregation, while a date restriction generally belongs on the underlying dated facts unless the question explicitly asks otherwise.

### 30. How do window functions help this project?

Window functions calculate across related rows without collapsing them like GROUP BY. They support ranking, latest-snapshot selection and comparisons to previous periods. ROW_NUMBER can select one deterministic latest row per partition; DENSE_RANK can preserve metric ties; LAG can expose prior observations. Partition keys must reflect the analytical grain, such as source, player and exact format, otherwise unrelated observations can contaminate one another.

### 31. Compare ROW_NUMBER, RANK and DENSE_RANK.

ROW_NUMBER gives each ordered row a unique sequence. RANK gives equal ordered values the same position and leaves gaps after ties. DENSE_RANK preserves ties without gaps. Top Players uses dense metric ranking; a separate stable identity can order tied display rows without changing the tie definition. Adding a unique player ID inside the ranking window's ORDER BY would destroy ties, so tie ranking and deterministic presentation must be distinguished.

### 32. Why should career snapshots not be summed?

Career totals are cumulative observations at different times. If one snapshot reports 1,000 runs and the next 1,100, adding them reports 2,100 rather than the latest 1,100. The project chooses the latest committed snapshot per source, player and exact format. A history chart can compare snapshots over time, but deriving increments requires compatible definitions and careful correction handling. Different provider format labels are not automatically interchangeable.

### 33. How do you compute averages and rates safely?

Choose the correct denominator and guard against zero or missing values, often with NULLIF. Batting average uses dismissals, not total appearances; bowling economy uses runs conceded per over expressed through legal balls. The mean of individual strike rates differs from a pooled runs/balls strike rate, so the query must state which it answers. A meaningful answer explains both the formula and the population it includes.

### 34. How do CTEs improve analytical SQL?

A common table expression names an intermediate result so each step has a clear grain and purpose. A complex ranking can first select eligible facts, then aggregate, then rank, then present results. This helps reasoning and review, but a CTE is not inherently faster and its execution depends on the engine and plan. I would use it for clarity, then inspect the actual query plan and representative workload before claiming optimization.

### 35. How are analytical date windows defined?

Each question defines its own window rather than assuming one universal recent period. The project includes last-30-day, calendar-year and last-12-completed-quarter scopes, with an explicit analysis date. Calendar boundaries, leap days and exclusion of an incomplete current quarter matter. The synthetic fixture uses a fixed date for reproducibility. I would explain inclusive/exclusive boundaries from the question's actual SQL before interpreting an empty result as missing data.

### 36. What does LAG tell you about a missing quarter?

LAG returns a previous row in the ordered partition, which may not be the immediately previous calendar quarter. If one quarter is absent, comparing directly with the previous observed row can be mislabeled as quarter-over-quarter change. The quarterly analysis checks adjacency and preserves missing-period context; charts keep gaps unknown. A calendar scaffold can help display all periods, but filling missing performance with zero would invent an observation.

### 37. How would you optimize a slow SQL question?

First reproduce the workload and verify its result, then inspect EXPLAIN QUERY PLAN for scans, searches and sorting. Consider indexes on selective filters and join keys, and reduce rows before large joins where semantics allow. Check for join multiplication before treating latency as the only problem. Indexes cost storage and write work, so add them for measured query patterns. Results on the small teaching dataset are not proof of large-scale performance.

### 38. How is custom SQL kept read-only?

The executor combines SQLite read-only connections and query_only behavior with statement restrictions, a SQLite authorizer, an allowed-function policy and execution/result budgets. It is not protected merely by testing whether text starts with SELECT. Public-readonly access disables custom SQL entirely. The limits reduce misuse and resource exhaustion, but the cooperative execution budget is not an OS process sandbox or a guarantee against every possible resource threat.

### 39. How do you prevent SQL injection?

Values are bound as parameters instead of being concatenated into SQL. Dynamic identifiers such as table or column choices require a fixed allowlist because ordinary value binding cannot safely select identifiers. CRUD accepts known fields and validates types and relationships before writing. Custom SQL is intentionally user-authored SQL and therefore needs its own read-only authorization controls; parameterization alone does not make arbitrary statements safe.

### 40. What analytical interpretations should you avoid overstating?

Adjacent batting-position pairs are not verified ball-by-ball partnerships. A standard deviation describes variation in the observed sample, not a causal explanation of player reliability. A weighted performance score reflects chosen weights and available coverage rather than an objective universal ranking. Venue associations may reflect format, opposition and selection effects. I would state qualification rules and missingness alongside the chart instead of turning an observed association into a causal conclusion.

### 41. How does Streamlit rerun behavior affect the design?

Widget interactions rerun page code, so reads and pure rendering should be safe to repeat. API requests and writes must be triggered by explicit actions, not performed automatically during every filter change. Forms group intended submissions, and loaded edit versions remain in session state for conflict checking. An explicit service boundary makes the behavior testable even though the presentation executes repeatedly.

### 42. How do you use session state and caching responsibly?

Session state holds user choices such as timezone and loaded edit context. A cached process resource coordinates refresh timing and mutual exclusion. These have different scopes: one user's display preference should not change the database or another user's configuration, while a process resource is shared within that process. Cache reuse also requires considering database revision and freshness. Neither Streamlit caching nor session state is a replacement for durable database storage.

### 43. How do you choose the right visualization?

Bars compare ranked players or venues; lines show ordered trends; a heatmap reveals player-by-quarter patterns; scatter plots compare mean performance with variability. Separate run and wicket scales avoid implying that unlike units are directly comparable. Missing values stay missing and source tables remain available. A pie chart requires a meaningful complete whole; incomplete imported career coverage does not justify presenting players as shares of all cricket performance.

### 44. What does public_readonly protect, and what does it not?

It disables write paths and local custom SQL according to the application's access policy. The public demo entry also refuses unsafe live/local combinations and bootstraps only the reviewed synthetic sample. This is not identity authentication, role administration or a complete internet deployment security model. A public administrative site would require authenticated users, authorization, managed secrets, durable storage and tested operational controls before exposing edits.

### 45. Describe the testing strategy and what 519 passing tests prove.

The suite exercises pure transformations, temporary-database integration, SQL behavior, API contracts with injected responses and Streamlit page journeys. Error handling, ownership/version conflicts, import idempotency and public-readonly startup are included. The latest phase checks passed 519 tests plus lint and formatting. That demonstrates the checked cases; it does not establish exhaustive correctness, a coverage percentage, a successful container build or fresh provider authentication today.

### 46. How do you test APIs without spending quota?

Tests inject controlled transports and representative fixtures, including malformed, missing-field and failure responses. A default requests transport guard blocks accidental real requests in the suite. This makes behavior deterministic and keeps credentials unnecessary. The guard is not an OS-wide network sandbox, and mocks cannot prove the provider's current schema or availability. Separately recorded authenticated contract checks complement the offline suite.

### 47. What integration scenarios are most valuable?

A lifecycle scenario can create a player, add valid statistics, update with version checks, soft-delete and restore while verifying rankings and active views. An ingestion scenario can import a fixture, repeat it, attempt stale changes and confirm operator ownership remains protected. These cross module boundaries and test observable invariants. They are stronger than asserting private function calls that merely mirror the implementation and break on harmless refactoring.

### 48. How would you deploy this project and report its current status?

The prepared Docker demo uses cloud_app.py, a non-root image, a health check and a named volume for a synthetic public-readonly database. Compose binds host loopback port 8502. Configuration and six startup cases passed, but the Docker engine was stopped, so image build, container execution and hosted publication remain unperformed. I would next run those acceptance checks and validate restart persistence before giving anyone a deployment URL.

### 49. How would you scale and operate it reliably?

I would first measure demand, centralize refresh budgets, separate ingestion scheduling from browsing, and choose persistent storage appropriate to the deployment. A larger writable multi-instance service would likely need a server database and explicit authentication. Consistent backups must be restored in a drill, not merely created. Structured safe diagnostics should track failures and freshness without logging secrets. These are planned improvements, not features already validated by the local prototype.

### 50. What would you say were your main learning outcomes and next improvements?

I learned to preserve fact grain, source identity, cumulative snapshots and unknown values while moving from nested JSON to useful SQL and a dashboard. I also learned that transaction safety, ownership, UI reruns and honest coverage labels are part of data correctness. Next I would complete runtime deployment acceptance and visual deliverables, then broaden historical/player coverage and improve hosted access and operations. I would support each claim with a file, test or demonstration rather than inventing production experience.

## Evidence and practice

- [Architecture](03_system_design.md), [ER design](04_database_design.md) and [current folder map](folder_guide.md)
- [API operations](api_setup.md), [database operations](database_setup.md) and [CRUD guide](10_crud_guide.md)
- [All SQL questions](../sql/queries/README.md), [visualizations](13_visualization.md) and [testing](15_testing.md)
- [Deployment and pending acceptance](16_deployment.md), [user demonstration sequence](user_guide.md) and [future improvements](future_improvements.md)

Practice answering without reading, then open the relevant module or SQL question and explain one concrete example. For SQL, identify grain, joins, filters, grouping, NULL behavior, ties and date boundaries before discussing performance. For a code walkthrough, follow page → UI → service → database, then explain the explicit refresh path separately. If you have not measured latency, scale or coverage, say so rather than inventing a number.

## Phase completion

Completed: 50 answered interview/viva questions covering Python, APIs, database design, SQL, Streamlit, visualization, testing, security boundaries and system design; a short introduction; evidence links; and practice guidance. README, documentation index, requirement status and the dashboard phase label point to this handoff.

Concepts reinforced: design tradeoffs, data correctness, reproducibility, defensive boundaries and evidence-based technical explanation. All 18 teaching phases now have their requested material. Screenshot captures/video, Docker/container/host runtime acceptance, broader provider history and other listed future work remain pending; phase completion does not close those product acceptance items.
