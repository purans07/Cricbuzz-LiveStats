# Phase 12 — Page 3: Top Players

Home, Live Matches and Top Players are implemented. Analytics, CRUD and Settings remain pending; Phase 12 is still in progress.

## Purpose and design explained before implementation

Top Players compares saved **career** statistics from a selected source and exact format. It must not present a handful of imported profiles as the world's leading players, sum multiple cumulative career snapshots, mix formats or reconstruct careers from incomplete match scorecards. Native tables and profiles are built now; charts belong to Phase 13.

Keep UI controls in `ui/top_players.py`, ranking logic in `services/top_players.py`, persistence in the existing central read-only database manager, and profile reads in the existing PlayerStatsService. The route file only delegates rendering. No API client is created by this page.

## Components, inputs and outputs

| Component | Input | Output |
| --- | --- | --- |
| Navigation | Top Players | Third registered page alongside Home and Live Matches |
| Dataset | Configured dataset, Saved sample, Saved provider | Session-only selection; no private file edits or database initialization |
| Source | One source with active latest career rows | Source-scoped ranking, never merged providers |
| Format | One exact stored format for the source | Isolated format statistics with original format code |
| Rank by | Seven allowlisted measures | Descending totals/batting rates or ascending bowling rates |
| Display limit | 10, 20, 50 or 100 | Deterministic maximum displayed rows |
| Minimum career matches | Integer 0–100,000 | Optional sample-size filter |
| Coverage metrics | Saved eligible records | Players after match filter, known ranking values and displayed count |
| Import context | Selected latest snapshots | Oldest/newest snapshot times, timezone, per-row coverage and import date |
| Results table | Ranked latest career rows | Shared dense ranks, totals and derived/reported rates |
| Player selector | One displayed player's stable ID | Stored name, role, batting/bowling styles and career scope |
| Reload saved statistics | Button | Reread local data with no HTTP call |

Configured dataset preserves a custom validated path. Saved sample/provider choose their fixed project database files while retaining access mode and timezone. This does not change Home/Live Matches selections or rewrite .env. Missing targets show an error without being created or repaired. Readonly visitors can use every Top Players control because the page exposes no writes or provider refreshes.

Formats remain exact: TEST, ODI and the provider's INTERNATIONAL_T20 are not added together; INTERNATIONAL_T20 is not automatically renamed T20I. The sample's T20I and provider's INTERNATIONAL_T20 therefore appear under their actual stored categories. Source/format options are obtained from available latest career records rather than hardcoded promises of coverage.

## Backend logic and database calls

```text
main.py -> pages/03_Top_Players.py -> render_top_players()
  -> validated selected settings and existing Database
  -> TopPlayersService.catalog()
  -> source / format / measure / limit / minimum controls
  -> TopPlayersService.leaders()
  -> PlayerStatsService.profile(selected_local_player_id)
  -> render and dispose database resources in finally
```

`catalog()` executes one grouped SELECT over v_latest_career, sources and formats. The view already excludes deleted players and uncommitted batches and selects the latest committed snapshot per player/format/source using fetch time and batch-ID tie-breaker. It returns only combinations with saved data.

`leaders()` validates source/format IDs, a 1–100 row cap, a 0–100,000 minimum-match filter and the fixed measure name. It runs two SELECTs inside one read transaction: coverage counts/date range and ranked rows. Both use the same metric CTE. Values are bound parameters. Only metric column names and ASC/DESC tokens are interpolated from a fixed allowlist; arbitrary UI SQL or paths are not accepted.

The metric CTE selects one latest career row per player for the chosen source/format, joins the player's label and import coverage and applies the match filter. It does not SUM runs, wickets or matches over cumulative snapshots. The selected record's matches_played is the format-specific career count, not the number of match scorecards stored in this database.

Profile details use the existing parameterized active-player query with an optional role join. An absent role/style remains Unknown. The profile read occurs after the leaderboard transaction; if another operator deletes the player between them, the UI explains that the profile changed and asks for a reload. Names do not identify or merge players.

## Ranking and rate definitions

| Measure | Direction | Interpretation |
| --- | --- | --- |
| Most runs | Descending | Known career runs |
| Highest score | Descending | Known highest individual innings score |
| Most wickets | Descending | Known career wickets; zero is valid |
| Batting average | Descending | Runs / dismissals |
| Strike rate | Descending | 100 × runs / balls faced |
| Bowling average | Ascending | Conceded runs / wickets |
| Economy rate | Ascending | 6 × conceded runs / legal balls bowled |

Compute ratios when the denominator is known and positive. Only when the denominator is NULL may the matching reported ratio be used. A known zero denominator remains undefined, even if a provider supplies a placeholder zero or a reported number. If the denominator is positive but a required numerator is unknown, the calculated rate is NULL; it is not filled from a reported value. No cricket-overs decimal is used in economy calculations.

Unknown values for the selected measure are excluded from ranking and counted by the coverage difference. Known zero totals remain eligible. Minimum matches 0 means no match-count filter, including rows with unknown matches_played. A positive minimum requires a known count meeting that minimum. This filter is optional and no minimum dismissals, balls or wickets threshold is silently applied; small-sample rate leaders should be interpreted accordingly.

Use DENSE_RANK on the unrounded selected metric, with equal values sharing a rank and no gaps. Player ID stabilizes display order but does not break the shared rank. The limit caps rows rather than complete rank groups, so a tie at the boundary can be truncated. Rounding to two decimals happens only when presenting rates. There is no combined cross-format or weighted global talent ranking here.

Coverage counts and the import range describe all rows passing the source/format/match filter, including unknown selected measures. Displayed count describes only known values after the row cap. Each displayed row also shows its own import time and completeness. The range does not establish that all players were measured on the same date. A warning appears when fewer than ten players pass the match filter; this is a visibility rule, not a statistical sample-size guarantee.

## Reruns, errors and refresh boundary

No leaderboard/result cache is introduced: each UI rerun reads the current committed local records, so new imports and soft deletes are reflected after reload. There are no open transactions or credentials in session state. Downloads available through native table controls contain only displayed data.

Page visits, filters and reloads make no HTTP requests and spend no API quota. Career enrichment remains available through the verified explicit player-import workflow described in the API guide/CLI. This page does not reuse the match-refresh buttons to fetch player data or infer a career from match-level performances.

Missing career data, a zero-row filter and a missing database are distinct states. The empty-career state explains that scorecards alone do not establish career totals. Bad configuration and database errors produce safe messages; private keys, connection URLs and raw exception details are not displayed. The page never initializes, migrates or edits a target.

## Observed results and coverage limits

The existing sample contains 12 fictional players with latest career rows in three formats. The default row cap displays ten players. These are instructional records, not real professional leaderboards.

The saved provider dataset contains career snapshots for Temba Bavuma only, in TEST, ODI and INTERNATIONAL_T20. His saved ODI runs are 2,168 and Test runs 3,993. The page displays one player and a limited-coverage warning. It does not claim that he leads all players worldwide. Player roles/styles and bowling data are displayed only where stored and defined; blank rates are not filled with invented zero values.

[Read-only execution evidence](12_03_top_players_result.json) includes the available catalog and run/highest-score/wicket rankings for each source/format in both working databases. No new upstream request was made, and those databases were not modified. The browser was checked on the running local page in addition to isolated Streamlit tests.

## Files and concepts learned

- `services/top_players.py`: catalog, guarded metric CTE, coverage and dense ranking.
- `ui/top_players.py`: controls, source/format context, tables and profile view.
- `pages/03_Top_Players.py`: route.
- `main.py` and `ui/home.py`: three-page navigation and updated roadmap.
- `tests/test_top_players.py`: focused service and Streamlit checks.
- This guide, the execution report, README and requirements progress update.

Concepts learned: cumulative snapshots versus match facts, latest-row views, source/format isolation, unknown versus zero, ascending versus descending rankings, raw-value dense ranks, sample-size filters, safe dynamic SQL allowlists and uncached local reruns.

## Verification and next page

Eleven focused tests cover latest committed snapshot selection without summation, failed-batch fallback, unknown/zero values, denominator rules, ascending bowling rates, ties and stable limits, unknown match counts/deleted profiles, source/format isolation and input validation, Streamlit filters with no HTTP, reread after changes, missing/empty databases and captured-provider career rendering in public-readonly mode.

Full suite: 413 tests passed; lint, formatting and whitespace checks pass. Local read queries support both the preserved schema-1 sample and schema-2 databases. Larger career populations may need revision-aware caching after profiling; the present dataset is small.

Top Players implementation is complete. Charts/global historical population remain pending their respective milestones; no coverage or visualization acceptance is invented. Analytics is next within Phase 12.
