# Phase 13 — Visualization

Phase 13 adds interactive Plotly charts to the existing Top Players and Analytics pages. Charts consume the reviewed service/SQL results rather than reimplementing cricket calculations or fetching new API data. All six Phase 12 pages remain available. Phase 14 has not started.

## Chart selection explained before implementation

Choose a chart by the question, observation grain, units and data coverage. A chart cannot repair missing history, turn cumulative snapshots into match facts or establish a complete population. All provider data remains explicitly saved and potentially old; all sample figures remain fictional.

| Visualization | Location and data | Why it is useful | Important interpretation |
| --- | --- | --- | --- |
| Horizontal ranking bar | Top Players, selected latest source/format/measure | Compare magnitudes and read long player labels | First 20 displayed rows, preserving service order; lower bowling average/economy is better |
| Player comparison bars | Top Players, 2–6 selected displayed players | Compare career runs and wickets side by side in separate charts | No mixed-unit sum or normalization; snapshots may have different dates and opportunities |
| Quarterly line | Analytics → Visualizations → Q25 | Follow the same player's scoring/rate changes over elapsed quarters | Actual SQL means, no forecast; gaps are blank and lines do not bridge them |
| Player/quarter heatmap | Same Q25 rows and selected measure | Spot relative high/low quarters across selected players | Color scale is relative to the current selection; missing cells are not zero |
| Consistency scatter | Analytics → Visualizations → Q19 | Compare scoring level with score variability | Mean innings runs versus population standard deviation; hover shows innings count |
| Venue comparison bar | Analytics → Visualizations → Q14 | Inspect qualifying player–venue economy or wicket records | Separate SQL result rows, not an overall venue average or a new ranking |
| Pie chart (discussed, not used) | Would require a complete mutually exclusive whole | Useful for composition when categories partition a meaningful total | Current imported careers/rankings overlap or omit records; a pie would imply unsupported shares |

Scatter plots can reveal associations, not prove causation. Heatmaps emphasize patterns, not statistical significance. Lines show observed changes rather than fitted forecasts. A consistent low scorer is not necessarily a better batter. More wickets or runs may reflect greater opportunity rather than superior efficiency. These distinctions belong beside the charts, not just in an implementation note.

## Top Players: inputs, outputs and backend logic

The existing dataset/source/format/measure/minimum-match/display-limit controls still determine the table. The chart uses the exact unrounded ranking_value and existing rank/match-count/import fields from TopPlayersService. No older career snapshot is added, and no second source or format is merged.

The horizontal bar displays at most the first 20 rows already returned for the table. It does not reorder ascending measures or create a different leaderboard; the first service-ranked row remains at the top. Numeric axes include zero so bar length comparisons are meaningful. Labels include stable local player IDs to distinguish duplicate names. Hover provides rank, matches and snapshot import time. Titles include the selected dataset mode, source and exact format.

The comparison selector offers only currently displayed player IDs, defaults to the first two and caps selection at six. Fewer than two players produces an explanation rather than a fabricated comparison. Career runs and wickets are drawn in separate figures with separately labeled axes. Unknown values have no bar; known zero remains zero. All original coverage counts, warnings, exact-format notes, row dates and source labels remain on the page.

Live data currently has only one enriched career player. A one-player ranking chart is permitted and clearly scoped; the comparison cannot run until at least two imported displayed players exist. This is not a worldwide leaderboard or a statement that one player is globally best.

## Analytics visualization workspace

A third Analytics workspace, Visualizations, provides a dedicated chart-analysis selector. It uses the existing AnalyticsService restricted saved-query runner with its 500-row/result/time budgets. Charts read saved data on rerun; they do not call the provider or alter saved SQL. If a result is clipped, the UI warns that the chart is based on the clipped result. Chart source rows remain inspectable in an expander.

### Quarterly trends and heatmap — Q25

The analysis date controls the original twelve-completed-quarter window. The original SQL requires six observed quarters and at least three batting matches in every observed quarter, combines ordinary Test innings into match totals, and retains its missing-metric rules. The SQL's format-combined scope is disclosed; changing format mix can change apparent trends. The selected source rows are current saved match history, not cumulative career snapshots and not verified complete careers.

Choose up to six eligible stable player IDs and either average runs per batting match or arithmetic mean match strike rate. These two units are never put on one axis. The line chart exposes change over calendar quarters, while the heatmap shows the same metric as a player-by-quarter matrix.

The pure quarter-grid helper enumerates every quarter from the earliest to the latest selected observation, including year boundaries. For each player, absent quarters and unknown metrics produce None. Plotly `connectgaps=False` prevents a line from implying continuity across gaps. Heatmap gaps have no value and no misleading hover; they are not filled with zero. Stable IDs prevent same-named players from becoming one series. Hover on the line includes the quarter's actual batting-match count.

Color scales are selection-dependent; equal color intensity in two different selections need not mean equal numbers. Read the colorbar and hover values. The line does not draw future projections or refit an OLS model in Python; Q25's existing slope/career-phase fields remain available in source rows. A displayed phase is still the documented teaching heuristic, not a validated forecast.

### Consistency scatter — Q19

Use the original Q19 result: known ordinary-innings scores with at least ten balls faced, for matches starting from 2022 onward. X is mean qualifying innings runs; Y is population standard deviation of those scores. Both axes use runs. Every result row is a separate point; unknown coordinates are omitted, and zero remains valid.

Hover includes the SQL row's player name, result-row number and innings count. Q19's output lacks persistent player IDs, so the renderer never groups by name or joins names back to identities. Row numbers distinguish result records for this rendering only, not enduring player IDs. Coincident points may overlap. A single innings has standard deviation zero but does not establish reliable consistency; this limitation appears next to the plot.

### Venue comparison — Q14

Reuse the original Q14 qualification: at least three matches per player/venue, with each contributing match having at least 24 known legal balls bowled. Select mean match economy (runs per six-ball over) or total wickets. The renderer does not average venue rows, pool economies differently or treat unknown values as zero.

The bar chart shows the first 20 known selected values in SQL result order. This is explicitly a comparison view, not a newly sorted venue leaderboard. Labels include player name, venue name and a unique result-row number; duplicate names remain separate rows instead of being aggregated or conflated. Hover shows qualifying match count. Row numbers are rendering identifiers, not permanent venue/player identities. The full result/source table retains other qualifying records.

## Rendering, style and interactions

`utils/charts.py` contains pure figure builders with no database, network or session-state access. `ui/visualizations.py` explains choices, obtains saved result rows and renders native Streamlit Plotly elements. `ui/top_players.py` and `ui/analytics.py` integrate these components without moving SQL metric logic into the chart layer.

The navy surfaces and teal/gold/pink/blue palette continue the adopted Retail Arcade-inspired direction. Figures have descriptive titles, axis units, stable labels and readable hover details. Player lines have labeled legends and markers in addition to color. Numeric bars start at zero. Native Plotly interactions support hover, zoom and legend visibility; the source table remains the exact-value alternative to reading color/position.

Long venue/player labels and many records can be dense, so charts cap their category rows while keeping the underlying table accessible. Chart caps do not pretend to be a new analytical top-N query. No 3D, radar or dual-axis comparison is used to mix incomparable units. Pie charts remain a documented choice rather than an artificial requirement.

## Files created or changed

- `utils/charts.py`: ranking/comparison bars, quarter-grid lines and heatmap, consistency scatter and venue bars.
- `ui/visualizations.py`: chart controls, interpretation, coverage/empty/clipped states and source rows.
- `ui/top_players.py`: leaderboard and selected-player charts alongside the existing table/profile.
- `ui/analytics.py`: saved-query visualization workspace.
- `main.py`, Home/Settings copy and README: current visualization status.
- `tests/test_visualizations.py`: pure figure and actual Streamlit checks.
- This guide and `13_visualization_result.json`: phase explanation and read-only evidence.

## Verification and completion

Fourteen new cases verify exact ranking values and order, stable-ID labels, 20-row caps, unknown versus zero bars, explicit missing-quarter gaps across a year boundary, disconnected gaps, heatmap identity/missing cells, separate same-named venue rows, zero dispersion and innings counts, empty serializable figures, actual Top Players ranking/comparison rendering, all three Analytics chart analyses without HTTP, and an empty-chart state without fabricated values.

All chart builders use query results. Tests inspect their trace data rather than simply asserting that a figure object exists. Existing leaderboard, SQL, form, access and navigation checks continue to run. The full suite passes **492 tests**, with lint, formatting and whitespace checks passing. No working-data edits, upstream HTTP requests or new API quota were used.

The read-only phase report records sample/live chart input counts and eligibility. It documents 144 Q25 quarterly sample rows, while the limited live match history does not qualify for the long-history venue/quarterly charts. Actual provider data remains available for its saved career ranking and Q19 qualifying innings, with the original source/coverage limits.

**What we completed:** explained chart suitability and implemented bar, line, scatter, heatmap, trend, player and venue views in the existing app. Pie suitability was discussed without inventing a complete whole. Table outputs and interpretation remain alongside the charts.

**Concepts learned:** visual encodings, observation grain, unit separation, stable identities versus result-row labels, missing-value gaps, descriptive trends versus forecasts, chart sampling/caps and coverage-aware comparison.

**Next phase preview:** Phase 14 — Error Handling will review database/API/connection/JSON/validation/Streamlit exceptions, current safe messages and failure recovery. Phase 13 is complete; Phase 14 awaits the user's next request.
