# Phase 12 — Page 2: Live Matches

Home and Live Matches are implemented. Top Players, Analytics, CRUD and Settings remain upcoming; Phase 12 is not complete.

## Purpose and concepts explained before implementation

The match centre turns existing verified API imports into an inspectable page: choose a dataset, filter saved matches, inspect venue/status/source information and read batting/bowling scorecards by innings. Provider requests occur only on explicit button clicks. Opening a page, choosing another match, switching tabs or changing filters never fetches upstream data.

Separate presentation from operations. `ui/live_matches.py` renders Streamlit controls; `LiveMatchService` reads stored records; `RefreshCoordinator` enforces target eligibility and request scheduling, then reuses `MatchService`, the existing verified normalizers, HTTP client and atomic ingestion. Do not move provider JSON parsing or credentials into page code. Use source-specific external IDs for provider requests, never a local database ID in the upstream URL.

## Components, inputs and outputs

| Component | Input | Output |
| --- | --- | --- |
| Sidebar route | Live Matches | Registered page next to Home |
| Dataset selector | Configured dataset, Saved sample, Saved provider | Session-only target choice; existing settings access mode is preserved |
| Dataset label | Validated target mode | Fictional training label or saved-provider warning |
| List refresh | Explicit button | One bounded provider operation, validated import and refreshed local list |
| Status filter | Ongoing in saved data, all, completed, scheduled, abandoned, unknown | Matching stored records and total counts |
| Match selector | Stable local match ID | Team names, description, format, venue, city, status and start |
| Source context | Stored source and batch metadata | Import timestamp in configured timezone and coverage label |
| Scorecard refresh | Explicit button for selected verified provider match | One regular-scorecard request and atomic import |
| Innings expanders | All stored innings for selected match | Team, total runs/wickets and cricket overs |
| Batting tab | Active ordinary-innings batting records | Player, position, runs, balls, boundaries, dismissal and derived strike rate |
| Bowling tab | Active ordinary-innings bowling records | Player, overs, maidens, conceded runs, wickets and derived economy |
| Row provenance | Per-performance batch/ownership | Imported time and api/manual/override ownership |

The configured target can be a custom validated path. Saved sample/provider select the project's fixed data/runtime/sample.db or live.db respectively; they do not rewrite .env, change the Home selection, initialize files or migrate old schemas. The existing display timezone and access mode remain in force. A missing target produces a useful message without creating a database.

Saved status is explicitly labeled. A provider snapshot from October 22 is not a claim that a match remains in progress today. “Ongoing in saved data” filters the normalized stored live status, including recorded stumps/lunch/toss states. Match absence in a later provider list does not prove completion; older records are retained rather than automatically deleted or relabeled.

## Database reads and cricket calculations

`LiveMatchService.matches()` executes one fixed SELECT joining matches to format, optional venue/source/batch and participant slots 1 and 2. Each slot is unique, so innings cannot multiply match counts. Missing metadata stays visible as Unknown. All statuses are read; filtering happens locally in this small dashboard dataset.

`scorecard(match_id)` validates a positive integer, then uses one read transaction to fetch all innings, ordered by innings number. For each innings it fetches batting and bowling rows through the active views, joining player labels and their own import batches. Every user-selected ID is bound as a SQL parameter. SQL table/column/order fragments come only from a fixed code tuple, not UI input. Performance reads exclude deleted rows/players and super overs via existing views. A stored super-over summary is labeled separately and does not fabricate ordinary performance rows.

Stored legal balls are converted with `balls_to_overs`: 26 balls means 4.2 overs, never decimal division by six. Strike rate is 100 × runs / balls faced. Economy is 6 × conceded runs / legal balls. Unknown inputs or a zero denominator produce missing rates, not zero. Known zero runs remain zero. Do not infer totals by adding a partial batting table, infer a winner from unparsed status prose, or infer not-out status from a missing dismissal.

The innings summary and individual performance rows may come from different imports or operator overrides. Their times/ownership are shown separately. The match import timestamp is not silently relabeled a scorecard fetch time. An empty detailed table can coexist with an innings summary; the UI explains that detail has not been saved. No batting/bowling row is manufactured from the summary.

## Explicit refresh workflow

```text
button click
  -> validate writable live target and schema 2
  -> for a scorecard, resolve provider external match ID and two verified teams
  -> acquire process-wide nonblocking refresh lock
  -> check cooldown
  -> privately load verified API settings
  -> check provider/version match
  -> reserve minimum 30 seconds, or a longer configured minimum
  -> create client and fetch outside a write transaction
  -> existing normalizer validates provenance and JSON
  -> existing ingestion commits atomically or reports duplicate/stale
  -> reread local data for display
  -> close client and release lock
```

The two operations remain `live_matches` and `match_scorecard`, using the reviewed v2 contract's actual `/matches/v1/live` and `/mcenter/v1/{matchId}/scard` paths. Schema/mode/access and selected-match identity are checked before loading API credentials or spending quota. Scorecard refresh requires the known provider source for both match and participants. Arbitrary external IDs or endpoints cannot be typed into the page.

A cached **resource** shares only the coordinator lock and cooldown across sessions/reruns in this single process, not credentials, HTTP clients, open connections or result data. One refresh at a time is allowed; another receives a useful wait message. A request reserves at least 30 seconds even if it fails. Retry-After can extend this delay. No blocking sleep or automatic polling is added. The existing HTTP policy still enforces connect/read timeouts, response limits, redirect refusal, retry policy and operation budget. Manual refresh can spend quota; changing a filter cannot.

An empty valid list is a successful import with zero returned matches, not a transport error. The confirmation reports how many matches were in that response and explains that older saved records remain. Successful ingestion is reported only after the operation returns. Older provider snapshots are identified as stale and do not overwrite newer saved records. Duplicate requests reuse existing ingestion safeguards.

This cooldown is a local protective rule, not the provider's actual quota enforcement. It resets on process restart and does not coordinate separate app processes, other tools or CLI requests. Provider quota limits continue to apply. Do not deploy multiple instances expecting this lock to coordinate them.

## Failure, cache and access behavior

Sample and public_readonly targets disable refresh buttons; authoritative service checks also reject these requests if bypassed. They can still browse saved scorecards. Old schema-1 sample reads remain supported, while live refresh requires schema 2; migrations remain explicit.

Authentication/subscription rejection, rate limits, network/timeouts, invalid/mismatched JSON, mock data and database failures produce safe messages. Provider response bodies, raw exception details, private keys and database URLs are not rendered. Failed normalization or atomic import preserves the existing dataset. The UI does not claim a successful refresh on an error. Historical saved records remain browsable after a failed request. Missing-database and empty-filter states are distinct from zero scores.

Match and scorecard results are intentionally uncached for now: every UI rerun reads current committed local records, so explicit refreshes and CRUD changes do not leave stale cached tables. This is suitable for the current small datasets; the per-innings detail reads are a bounded-by-match N+1 pattern. Larger scorecards/history should use bulk performance reads and revision-aware result caching after profiling. No performance claim for a large production warehouse is made.

## Files and learning checkpoint

- `pages/02_Live_Matches.py`: thin route.
- `ui/live_matches.py`: dataset/filter/match controls, explicit refresh actions, states and innings tables.
- `services/live_matches.py`: saved queries, provider preflight, serialized refresh and safe confirmation metadata.
- `main.py`: Home and Live Matches navigation, Top Players preview.
- `ui/home.py`: updated page roadmap.
- `tests/test_live_matches_page.py`: isolated service, captured-provider and Streamlit tests.
- `documentation/12_02_live_matches_result.json`: read-only evidence for the existing sample/live databases.
- README and requirements checklist: current page status.

Concepts learned: local versus upstream identities, source/freshness labels, parameterized scorecard reads, cricket overs versus decimals, native tables/tabs, explicit events, process-local resource caching, cooldowns, atomic import reuse and incomplete/empty/error states.

## Validation and practical limits

Thirteen focused checks cover match/innings grain, active rows, provider list followed by regular scorecard import, correct external-ID routing, cooldown and Retry-After persistence, concurrent request refusal, sample/readonly/schema preflight before API setup, unverified IDs, valid empty responses, sample empty/filter/scorecard UI without HTTP, one request per click rather than filter reruns, redacted error UI and missing files. These use temporary databases and captured/synthetic responses, not live credentials.

The browser preview was checked against the existing saved provider database: three matches have an ongoing saved status out of four stored matches; South Africa–Australia has three innings with 27 batting and 19 bowling rows. Existing sample data has 72 completed matches and a clear empty ongoing filter, with full fictional scorecards available under All saved matches. No current upstream HTTP request was made during this implementation; refresh integration is verified with captured provider payloads and the existing Phase 9 authenticated evidence, not claimed as a fresh live acceptance call.

Full suite: 402 tests passed; lint, formatting and whitespace checks pass. Working sample/live databases were read only for the execution report and browser inspection. Live API refresh and its writes occur only when the operator explicitly presses a refresh button.

Live Matches implementation is complete. Top Players is the next page in Phase 12. Phase 13 visualization work has not started.
