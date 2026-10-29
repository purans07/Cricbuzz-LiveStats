# Phase 11 — Question 25: quarterly player evolution

## Assignment before SQL

Track quarterly averages for runs and strike rate, compare each quarter to the previous quarter, identify improving/declining/stable performance and determine the player's recent career trajectory. Use Career Ascending, Career Declining and Career Stable labels. Only analyze players with at least six quarters of data and at least three matches per quarter.

## Scope, eligibility and missing data before SQL

Use the **last twelve completed calendar quarters**, a three-year teaching window. For the October 2026 sample and live snapshots, bind `window_start=2023-10-01T00:00:00Z` and `window_end=2026-10-01T00:00:00Z`. The lower bound is inclusive, upper exclusive. The in-progress 2026 Q4 is excluded. A caller choosing a later report date should compute that date's latest completed-quarter boundary and subtract twelve calendar quarters; pass normalized UTC boundaries on the first of January, April, July or October at midnight. The SQL relies on that input contract and does not validate arbitrary strings or call the machine clock.

Quarter membership uses the match's scheduled UTC start, not its end or display timezone. A match spanning a quarter boundary belongs to its start quarter. Require completed matches and an active ordinary-innings batting record. DNB appearances do not become zero-run batting matches. Combine all ordinary innings for a player/match before counting matches or averaging. Super overs, deleted rows and deleted profiles are excluded. Zero runs are valid. Unknown dates fall outside the comparison.

Eligibility means **at least six distinct observed quarters**, and **every observed quarter in the bound window must have at least three distinct batting matches**. A seventh observed quarter with two matches disqualifies the player; we do not silently discard weak quarters to obtain six good ones. Quarters need not be consecutive. Entirely absent quarters are gaps, not zero performances, and are not counted as observed quarters. A calendar span of six quarters with only five observed quarters does not qualify. The sample has twelve observed quarters and six matches per quarter for each player.

Unknown runs or balls remain in the appropriate match/quarter. A quarterly run average requires known runs for every contributing innings/match. A quarterly strike-rate average requires every match's runs and balls known and every match's balls positive. A zero-ball match has an undefined individual rate, so the whole quarterly mean rate is NULL; we do not discard it to improve apparent coverage. Run averages may still be available. Career phase needs both complete quarterly metric histories; missing metrics leave it NULL. Rows remain visible for history-eligible players so unavailable metrics are inspectable.

Stored data may omit whole matches or innings; cell completeness cannot prove import completeness. This is an analysis of the chosen saved database, not a verified full career. Like Q23, filtering current records by scheduled start is not a versioned point-in-time reconstruction. A match now completed could have been unfinished at an earlier cutoff. The report makes no backtesting claim.

All formats are combined to preserve one timeline per player, since the assignment gives no format restriction. Test match totals and limited-overs scores/rates have different scales; format mix can drive apparent trends. A later dashboard can offer separate format windows with eligibility re-evaluated per format.

## Metric and trajectory rules before SQL

Quarterly average runs = mean of player match totals. Quarterly average strike rate = **arithmetic mean of individual match rates**, each 100 × match runs / match balls. This follows Q16's average-rate interpretation; it differs deliberately from Q23's pooled-window strike rate. Neither is a dismissal-based batting average. Show distinct batting-match counts alongside each mean.

Encode a quarter as `year × 4 + zero_based_quarter`. SQLite integer division maps months 1–3 to zero, 4–6 to one, 7–9 to two, 10–12 to three. This index advances by one across a year boundary. LAG retrieves the previous observed row, but changes are calculated only if its index is exactly current minus one. First observations and gaps have NULL changes/trend and an explicit comparison status. Do not compare 2025 Q1 directly with 2024 Q3 as if they were consecutive quarters.

The brief supplies no thresholds or trajectory formula. These are transparent **project heuristics**, not official cricket standards or a predictive model:

| Output | Rule using unrounded values |
| --- | --- |
| Quarterly Improving | Both run-average and strike-rate changes ≥0, with at least one strictly >5 |
| Quarterly Declining | Both changes ≤0, with at least one strictly <−5 |
| Quarterly Stable | Remaining complete consecutive comparisons, including mixed directions |
| Career Ascending | Both fitted slopes ≥0, with at least one strictly >1 per calendar quarter |
| Career Declining | Both slopes ≤0, with at least one strictly <−1 per calendar quarter |
| Career Stable | Remaining complete histories, including mixed directions |

The run thresholds are runs per match (or per elapsed quarter for slopes); strike-rate thresholds are rate points (or points per quarter). Exactly 5 quarterly change and exactly 1 slope do not exceed the stated thresholds. Requiring both signs to agree avoids declaring clear improvement when one measure falls. Stable is therefore a broad policy bucket, not proof of no change or statistical equivalence. Missing values never become Stable.

Fit each metric across observed quarters with ordinary least squares (OLS):

```text
slope = SUM((quarter_index − mean_index) × (quarter_metric − mean_metric))
        / SUM((quarter_index − mean_index)²)
```

Use centered values rather than differences of large totals. Fit equal-weight quarterly means, not one observation per match: a quarter with more matches does not acquire extra weight. Gaps retain their actual elapsed-quarter spacing in the regression, even though they do not create artificial quarterly observations. At least six distinct quarters ensure a positive time variance; NULLIF still guards division. A single slope/phase per player is repeated on that player's quarterly rows. This is a recent three-year trajectory, not a conclusion about the player's whole lifetime career. No confidence intervals or significance test is implied.

## SQL concepts, relationships and execution plan before SQL

Use CTEs for match totals, quarterly means, history eligibility, centered OLS slopes, LAG comparisons and final classification. Conditional aggregation enforces completeness. A named window reuses chronological ordering for three LAG expressions. CASE distinguishes missing comparisons from stable ones. Round only final display columns, after threshold decisions.

`v_active_batting` supplies active player/innings batting facts with super overs removed. Join `matches` by match ID for starts and completed status. `players` supplies labels by ID; same-named identities stay separate. No career snapshot table is used: it lacks quarter-specific match history.

Filter dated completed fixtures; aggregate ordinary innings to match grain; group by player/calendar quarter; establish eligible histories; compute centered metric slopes; retrieve previous observed quarters and guard for calendar adjacency; classify raw changes and slopes; display in stable player/date order. Never count Test innings as distinct matches or drop NULL metric rows before checking the history.

## SQL

```sql
-- Q25: Completed batting matches in a caller-bound whole-quarter UTC window.
WITH match_scores AS (
    SELECT b.player_id,b.match_id,
           CAST(SUBSTR(m.starts_at,1,4) AS INTEGER)*4
             +(CAST(SUBSTR(m.starts_at,6,2) AS INTEGER)-1)/3 AS quarter_index,
           CASE WHEN COUNT(*)=COUNT(b.runs) THEN SUM(b.runs) END AS runs,
           CASE WHEN COUNT(*)=COUNT(b.balls_faced) THEN SUM(b.balls_faced) END AS balls
    FROM v_active_batting b JOIN matches m ON m.match_id=b.match_id
    WHERE m.status='completed'
      AND m.starts_at>=:window_start AND m.starts_at<:window_end
    GROUP BY b.player_id,b.match_id
), quarters AS (
    SELECT player_id,quarter_index,COUNT(*) AS batting_matches,
           CASE WHEN COUNT(runs)=COUNT(*) THEN AVG(1.0*runs) END AS average_runs,
           CASE WHEN COUNT(runs)=COUNT(*) AND COUNT(balls)=COUNT(*)
                     AND MIN(balls)>0
                THEN AVG(100.0*runs/balls) END AS average_strike_rate
    FROM match_scores GROUP BY player_id,quarter_index
), eligible AS (
    SELECT player_id,COUNT(*) AS observed_quarters,
           AVG(1.0*quarter_index) AS mean_quarter,
           CASE WHEN COUNT(average_runs)=COUNT(*)
                THEN AVG(average_runs) END AS mean_runs,
           CASE WHEN COUNT(average_strike_rate)=COUNT(*)
                THEN AVG(average_strike_rate) END AS mean_strike_rate
    FROM quarters GROUP BY player_id
    HAVING COUNT(*)>=6 AND MIN(batting_matches)>=3
), slopes AS (
    SELECT e.player_id,e.observed_quarters,
           SUM((q.quarter_index-e.mean_quarter)*(q.average_runs-e.mean_runs))
             /NULLIF(SUM((q.quarter_index-e.mean_quarter)*(q.quarter_index-e.mean_quarter)),0) AS runs_slope,
           SUM((q.quarter_index-e.mean_quarter)*(q.average_strike_rate-e.mean_strike_rate))
             /NULLIF(SUM((q.quarter_index-e.mean_quarter)*(q.quarter_index-e.mean_quarter)),0) AS strike_rate_slope
    FROM eligible e JOIN quarters q ON q.player_id=e.player_id
    GROUP BY e.player_id
), previous AS (
    SELECT q.*,LAG(q.quarter_index) OVER w AS previous_quarter_index,
           LAG(q.average_runs) OVER w AS previous_runs,
           LAG(q.average_strike_rate) OVER w AS previous_strike_rate
    FROM quarters q JOIN eligible e ON e.player_id=q.player_id
    WINDOW w AS (PARTITION BY q.player_id ORDER BY q.quarter_index)
), changes AS (
    SELECT *,CASE WHEN quarter_index=previous_quarter_index+1
                  THEN average_runs-previous_runs END AS runs_change,
           CASE WHEN quarter_index=previous_quarter_index+1
                THEN average_strike_rate-previous_strike_rate END AS strike_rate_change
    FROM previous
)
SELECT p.player_id,p.full_name AS player_name,
       CAST(c.quarter_index/4 AS INTEGER) AS year,c.quarter_index%4+1 AS quarter,
       c.batting_matches,s.observed_quarters,
       ROUND(c.average_runs,2) AS average_runs,
       ROUND(c.average_strike_rate,2) AS average_strike_rate,
       ROUND(c.runs_change,2) AS runs_change,
       ROUND(c.strike_rate_change,2) AS strike_rate_change,
       CASE WHEN c.runs_change IS NULL OR c.strike_rate_change IS NULL THEN NULL
            WHEN c.runs_change>=0 AND c.strike_rate_change>=0
                 AND (c.runs_change>5 OR c.strike_rate_change>5) THEN 'Improving'
            WHEN c.runs_change<=0 AND c.strike_rate_change<=0
                 AND (c.runs_change< -5 OR c.strike_rate_change< -5) THEN 'Declining'
            ELSE 'Stable' END AS quarterly_trend,
       CASE WHEN c.previous_quarter_index IS NULL THEN 'first_observed_quarter'
            WHEN c.quarter_index<>c.previous_quarter_index+1 THEN 'quarter_gap'
            WHEN c.runs_change IS NULL OR c.strike_rate_change IS NULL
                 THEN 'incomplete_metrics' ELSE 'compared' END AS comparison_status,
       ROUND(s.runs_slope,4) AS runs_slope_per_quarter,
       ROUND(s.strike_rate_slope,4) AS strike_rate_slope_per_quarter,
       CASE WHEN s.runs_slope IS NULL OR s.strike_rate_slope IS NULL THEN NULL
            WHEN s.runs_slope>=0 AND s.strike_rate_slope>=0
                 AND (s.runs_slope>1 OR s.strike_rate_slope>1) THEN 'Career Ascending'
            WHEN s.runs_slope<=0 AND s.strike_rate_slope<=0
                 AND (s.runs_slope< -1 OR s.strike_rate_slope< -1) THEN 'Career Declining'
            ELSE 'Career Stable' END AS career_phase
FROM changes c JOIN slopes s ON s.player_id=c.player_id
JOIN players p ON p.player_id=c.player_id
ORDER BY p.player_id,c.quarter_index;
```

## Every SQL line explained

| Line | Explanation |
| --- | --- |
| 1 | Describe the explicit whole-quarter UTC scope. |
| 2 | Begin match-level batting totals. |
| 3 | Select stable player and match identities. |
| 4 | Extract year and multiply by four for the chronological quarter scale. |
| 5 | Add the zero-based quarter derived by integer month division. |
| 6 | Sum runs only when every ordinary innings has known runs. |
| 7 | Sum balls only when every ordinary innings has known balls. |
| 8 | Read active ordinary batting and attach match metadata. |
| 9 | Require a completed fixture. |
| 10 | Apply inclusive start and exclusive end UTC bounds. |
| 11 | Produce one row per player/match before counting matches. |
| 12 | Begin quarter aggregation. |
| 13 | Select player/quarter and count batting matches. |
| 14 | Average match runs only when all are known. |
| 15 | Check completeness of match runs and balls for rate averaging. |
| 16 | Require every individual match-rate denominator to be positive. |
| 17 | Average the individual match strike rates, not a pooled rate. |
| 18 | Group by stable player and calendar quarter. |
| 19 | Begin history eligibility and centering values. |
| 20 | Count observed quarters for each player. |
| 21 | Compute mean quarter index for centered regression. |
| 22 | Require every quarterly run mean to be known. |
| 23 | Compute the equal-weight mean of quarterly run means. |
| 24 | Require every quarterly strike-rate mean to be known. |
| 25 | Compute the equal-weight mean of quarterly strike-rate means. |
| 26 | Group histories by player. |
| 27 | Require six observed quarters and three matches in every observed quarter. |
| 28 | Begin the two fitted trend slopes. |
| 29 | Select player identity and history length. |
| 30 | Accumulate centered quarter/run cross products. |
| 31 | Divide by centered squared time distances, guarding a zero denominator. |
| 32 | Accumulate centered quarter/strike-rate cross products. |
| 33 | Divide by the same elapsed-quarter variance for the rate slope. |
| 34 | Join eligible centering values to their quarterly observations. |
| 35 | Produce one slope row per player. |
| 36 | Begin previous-observation retrieval. |
| 37 | Fetch the previous observed quarter index. |
| 38 | Fetch that row's quarterly run average. |
| 39 | Fetch that row's quarterly strike-rate average. |
| 40 | Restrict the quarterly rows to history-eligible players. |
| 41 | Define chronological ordering separately for each player. |
| 42 | Begin calendar-adjacent changes. |
| 43 | Check that the previous observation is the immediately preceding calendar quarter. |
| 44 | Subtract the previous run average only for adjacent quarters. |
| 45 | Apply the same calendar adjacency check to strike rate. |
| 46 | Subtract the previous rate only for adjacent quarters. |
| 47 | Read the LAG results. |
| 48 | Finish the CTE chain. |
| 49 | Select player identity and display name. |
| 50 | Decode the chronological index into year and one-based quarter. |
| 51 | Display both quarterly match count and total observed quarters. |
| 52 | Round the quarterly run mean for display. |
| 53 | Round the quarterly average match strike rate. |
| 54 | Round the run-average change. |
| 55 | Round the strike-rate change. |
| 56 | Withhold quarterly classification if either change is missing. |
| 57 | Require nonnegative changes in both metrics for improvement. |
| 58 | Require at least one change strictly greater than five. |
| 59 | Require nonpositive changes in both metrics for decline. |
| 60 | Require at least one change strictly less than minus five. |
| 61 | Label remaining complete comparisons Stable, including mixed signs. |
| 62 | Explain unavailable comparisons at the first observation. |
| 63 | Explain unavailable comparisons across a calendar gap. |
| 64 | Check whether adjacent-quarter metric cells are missing. |
| 65 | Distinguish incomplete comparisons from successful comparisons. |
| 66 | Display the fitted run slope to four decimals. |
| 67 | Display the fitted strike-rate slope to four decimals. |
| 68 | Withhold career classification if either fitted metric slope is unknown. |
| 69 | Require both slopes to be nonnegative for Career Ascending. |
| 70 | Require at least one slope strictly greater than one per quarter. |
| 71 | Require both slopes to be nonpositive for Career Declining. |
| 72 | Require at least one slope strictly less than minus one per quarter. |
| 73 | Label other complete trajectories Career Stable. |
| 74 | Attach each player's repeated history-level slopes to their quarterly rows. |
| 75 | Attach player names by stable identity. |
| 76 | Order players and quarters deterministically. |

## Execution and observed results

Run the query on an existing read-only database connection with the two normalized whole-quarter UTC parameters above. Sample and saved live data use the same twelve completed-quarter window, deliberately excluding the incomplete October 2026 quarter.

Sample: 144 rows, representing twelve quarters each for twelve fictional players. Three players are Career Ascending, one Career Declining and eight Career Stable under the documented heuristic. Sample Player 01 begins at 2023 Q4 with six matches, mean runs 73.00 and mean match strike rate 138.61. Its fitted slopes are +1.1748 runs per quarter and +0.4493 rate points per quarter, producing Career Ascending. Its first row has no prior-quarter comparison.

Live: zero eligible rows. The saved data has neither six qualifying historical quarters nor the necessary completed batting-match history. Do not extrapolate career phases from the single detailed unfinished Test scorecard or cumulative career snapshots.

The [execution report](11_q25_result.json) records all rows, exact bounds and actual query plans for both datasets. Working databases were read only and no provider quota was used.

## Actual plan and optimization

```text
CO-ROUTINE previous
CO-ROUTINE (subquery-16)
MATERIALIZE quarters
MATERIALIZE match_scores
SCAN b USING INDEX idx_batting_player_match
SEARCH m USING INTEGER PRIMARY KEY (rowid=?)
SEARCH players USING INTEGER PRIMARY KEY (rowid=?)
SEARCH i USING INTEGER PRIMARY KEY (rowid=?)
SCAN match_scores
USE TEMP B-TREE FOR GROUP BY
MATERIALIZE eligible
SCAN quarters
USE TEMP B-TREE FOR GROUP BY
SCAN q
BLOOM FILTER ON e (player_id=?)
SEARCH e USING AUTOMATIC COVERING INDEX (player_id=?)
USE TEMP B-TREE FOR ORDER BY
SCAN (subquery-16)
MATERIALIZE slopes
SCAN e
BLOOM FILTER ON q (player_id=?)
SEARCH q USING AUTOMATIC COVERING INDEX (player_id=?)
USE TEMP B-TREE FOR GROUP BY
SCAN s
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
BLOOM FILTER ON previous (player_id=?)
SEARCH previous USING AUTOMATIC COVERING INDEX (player_id=?)
USE TEMP B-TREE FOR ORDER BY
```

The actual plan records keyed joins, materialized/reused aggregates, temporary grouping structures and the LAG window order. Existing match status/date, batting player/match and primary-key indexes are available; grouping on a derived quarter index still requires aggregation. Reduce innings to matches and then quarters before regression/window work. No new index is justified by the current small dataset. For a large warehouse, a separately validated quarter aggregate could support repeated reports, but it must preserve completeness and distinct-match rules.

## Validation and acceptance

Twelve focused checks cover ascending/declining/stable trajectories, centered OLS, six-quarter and three-match boundaries, missing-quarter gaps and actual time spacing, missing runs/balls, arithmetic mean of rates versus pooled rate, zero-ball matches, whole-quarter boundaries, unfinished/deleted/super-over exclusions, conflicting metric directions, exact slope thresholds and multi-innings Test match counts. Tests use temporary database copies.

The full suite passes 379 tests. Lint, formatting and whitespace checks pass. Q01–Q25 each have an implementation, lesson and saved sample/live execution evidence; Phase 11's individual SQL-question workflow is complete. Known source coverage and proxy limitations remain documented rather than replaced with invented data.

Phase 12 is next and has not started. Advance only when the user requests it.
