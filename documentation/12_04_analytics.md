# Phase 12 — Page 4: Analytics

Home, Live Matches, Top Players and Analytics are implemented. CRUD and Settings remain pending; Phase 12 is still in progress.

## Purpose and design explained before implementation

Analytics makes all 25 completed SQL questions usable in the dashboard, with their definitions, SQL, named parameters and tabular outputs visible. A separate local-only workspace supports exploratory custom SQL. Neither workspace fetches from the API or modifies records; administrative writes belong in CRUD.

Keep the registry, parameter rules and guarded query execution in `services/analytics.py`; layout/forms/results live in `ui/analytics.py`, and `pages/04_Analytics.py` delegates rendering. Do not copy the analytical calculations into Python or let page visitors choose filesystem paths. Saved SQL and lessons remain the reviewed Phase 11 files.

## Components, inputs and outputs

| Component | Input | Output |
| --- | --- | --- |
| Navigation | Analytics | Fourth registered page |
| Dataset | Configured dataset, Saved sample, Saved provider | Validated session-only target selection |
| Workspace | Saved questions or Custom SQL | Lesson controls or restricted query editor |
| Question | Q01–Q25 | Title, lesson, actual SQL, parameter controls and scope notes |
| Q22 output | Pair summary or Venue breakdown | Appropriate existing Q22 SQL variant |
| Lesson expander | Bundled allowlisted Markdown | Full definitions, line explanations and limitations |
| SQL expander | Registered SQL file | Inspectable SQL before execution |
| Analysis date | Valid date from 2000–2100 | Named date/time bounds for parameterized lessons |
| Statistics source | One stored source where required | Bound source_name, never merged sources |
| Output cap | 50, 100 or 500 rows | Bounded results with explicit truncation indicator |
| Run saved question | Form submission | Bound parameters, columns, rows and snapshot revision |
| Custom editor | One SQL statement, at most 20,000 bytes | Restricted read result or safe rejection |
| Schema expander | Stored dataset table/view definitions | Dataset structure for SQL learning |

The configured target preserves a custom validated database path. Saved sample/provider select fixed project files without rewriting private settings or initializing targets. Readonly visitors may run saved lessons; the custom editor is hidden and its service rejects custom execution independently of the UI. Session state is not an authorization authority.

## Saved-question registry and parameter logic

The explicit immutable Question registry contains exactly Q01–Q25, each with a fixed SQL filename, fixed lesson filename and required parameter tuple. Unknown IDs and inappropriate Q22 variants are rejected. The only extra saved output is Q22's already reviewed venue breakdown; no arbitrary path is accepted.

The original SQL files are executed unchanged. Some lessons intentionally have fixed years, thresholds or scopes; the date selector does **not** rewrite those SQL literals. The lesson and SQL make those fixed assumptions inspectable. Q13/Q24 explicitly warn that adjacent-position combined scores are proxies rather than measured stand runs. Q21/Q23/Q25 retain their documented teaching formulas, not claims of predictive validity.

| Question(s) | Bound input behavior |
| --- | --- |
| Q01 | as_of_date = chosen YYYY-MM-DD |
| Q02 | as_of_utc = chosen date at midnight UTC; window_start = preceding 30 days; query includes endpoint |
| Q03/Q07/Q09/Q11/Q20/Q21 | One selected source_name |
| Q22, both outputs | Half-open three-calendar-year window ending at chosen midnight UTC; earlier leap-day anniversary clamps to February 28 |
| Q23 | Exclusive start-time cutoff at chosen midnight UTC |
| Q25 | Twelve completed quarters ending at the first day of the chosen date's current quarter, with a start three calendar years earlier |
| Others | No bound parameters; original documented SQL scope applies |

The default analysis date is 2026-10-01 for reproducible sample lessons. Choosing today does not make old provider records current. Parameter values use binding, never SQL string interpolation. Invalid dates and missing required sources produce safe messages. Source options include stored source records; a source without suitable career facts can legitimately return no rows.

## Backend and database calls

```text
main -> Analytics route -> render_analytics
  -> load validated target settings
  -> allowlisted question / workspace controls
  -> Run form submission
  -> named parameter generation for saved questions
  -> AnalyticsService restricted reader
  -> one committed read snapshot + revision
  -> bounded rows and explicit truncation
  -> dispose resources in finally
```

Source choices use a small SELECT over sources. The schema helper reads only table/view definitions from sqlite_master, excluding SQLite internal names; it does not read project files, settings or credentials. No arbitrary PRAGMA is exposed to custom SQL.

The runner uses the existing Database read transaction, backed by an already-existing file opened read-only with query_only enabled and validated mode/schema. It reads dataset revision in that transaction, installs execution restrictions on the underlying SQLite connection, executes one statement with bound values, fetches bounded rows, and removes handlers before transaction cleanup. The pool uses fresh disposable connections, so per-query restrictions do not contaminate future operations. Duplicate column names are preserved as ordered columns/row arrays rather than silently overwriting dictionary keys.

No result cache is added. Each submission uses current committed data; changing questions/workspaces clears the rendered result. Form edits are submitted together when Run is pressed, so an unsubmitted date/source edit has not yet changed the last displayed result. The UI states this distinction. A result's revision identifies its database snapshot; another operator can commit later changes without retroactively altering displayed rows.

## Custom SQL restrictions

Custom SQL is enabled only when validated APP_ACCESS_MODE is local. Public-readonly service calls are rejected even if UI controls are bypassed. Saved lessons remain available in both modes.

Protection does not rely on a SELECT-prefix check. The connection itself is read-only/query-only and the SQLite authorizer permits SELECT, READ, recursive SELECT processing and a fixed set of safe built-in analytical/text/date functions. Everything else is denied, including writes, schema modifications, transaction commands, temporary-table creation, PRAGMAs, ATTACH/DETACH and extension/file functions. SELECT load_extension or readfile is therefore not a loophole. The standard driver's single-statement execute rejects statement chaining. Supported CTEs, joins and window functions remain usable.

| Budget | Applied behavior |
| --- | --- |
| SQL text | Maximum 20,000 UTF-8 bytes; editor also caps characters |
| Execution | Two-second deadline checked by SQLite progress handler every 1,000 virtual-machine operations |
| Rows | Validated service limit 1–500; UI offers 50/100/500 |
| Result payload | 1,000,000 bytes of encoded row values; stops and flags truncation |
| SQLite value length | 200,000 bytes |
| Expression depth | 100 |
| Columns | 100 |
| Binary output | Bytes represented by a size label rather than exposing binary payloads in the table |

The row/byte budgets do not silently alter the analytical SQL or inject a LIMIT into its text. A result exceeding a budget is flagged as truncated; a complete empty result is distinct from an output clipped before rows could be displayed. Oversized expressions/values can be rejected by SQLite; some formatting functions return NULL when a requested value exceeds SQLite's length budget.

These are local protective limits, not an operating-system process/memory sandbox or a mathematically exact wall-clock guarantee. A progress handler cooperatively interrupts SQLite work; a single native function or parsing step can run between callbacks. SQL/value/depth/column bounds reduce those risks, but custom SQL remains intended for a trusted local learner and stays disabled for public visitors. No assurance of safe arbitrary hostile workloads or multi-instance production isolation is made.

## Results, error handling and coverage

Results show displayed row count, dataset revision and a native table. Empty output explains that data coverage or eligibility may be insufficient. A truncation warning asks the learner to narrow the query. Unknown statistics remain NULL; no Python postprocessing fills them with zero. Existing SQL definitions continue to control cricket units, ratios, population statistics and pair/quarter grain.

Errors are converted to a safe query message: check statement syntax/names, use supported read operations or simplify an expensive query. Raw SQL exceptions, keys, connection URLs and file paths are not shown. Missing databases or bundled lessons have a separate setup warning; the page does not initialize, repair or migrate them. Writes/failed custom reads do not change revision or records. SQLite handlers are removed and cursors closed in finally blocks.

## Execution evidence and tests

[The execution report](12_04_analytics_result.json) records column names, bound parameters, displayed counts, truncation flags and first-three-row previews for all 25 questions plus the Q22 venue variant on both existing databases. Full historical lesson results remain in the Phase 11 reports. Working sample/live databases were read only; no HTTP or quota was used.

Forty-four focused test cases verify:

- Every saved question executes successfully under the same restricted reader, plus Q22 venue output.
- Calendar/leap-year parameter rules and invalid IDs/dates/missing sources.
- Rejection of writes, DDL, temporary tables, PRAGMA, ATTACH, transaction commands, file/extension functions, chained statements and a write behind a WITH clause.
- Supported recursive CTE/window queries, duplicate result-column names, row caps, result-byte limits, oversized SQL/value behavior and interruption of expensive recursion.
- Dataset/revision preservation and a usable connection after rejection/interruption.
- Local-only custom access, saved questions in readonly mode, actual Streamlit submission/results, clearing on question change, safe custom errors, missing targets without accidental creation and no implicit HTTP.

The full suite passes 457 tests; lint, formatting and whitespace checks pass. The running local browser was checked alongside isolated AppTest cases.

## Files and learning checkpoint

- `services/analytics.py`: explicit question registry, named parameter generation, schema/source reads and guarded SQLite execution.
- `ui/analytics.py`: workspaces, forms, SQL/lesson presentation and result states.
- `pages/04_Analytics.py`: route.
- `main.py` and `ui/home.py`: four-page navigation and updated roadmap.
- `tests/test_analytics_page.py`: saved-query, adversarial-reader and UI tests.
- This guide, execution evidence, README and requirements progress update.

Concepts learned: a saved-query registry, bound parameters versus SQL rewriting, forms and reruns, single-snapshot reads, SQLite authorizers, layered read-only enforcement, cooperative query interruption, explicit output budgets and coverage-aware result interpretation.

Analytics is complete. CRUD is next within Phase 12. Custom writes remain outside this workspace, and Phase 13 charts have not started.
