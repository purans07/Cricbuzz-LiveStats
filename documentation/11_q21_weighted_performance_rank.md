# Phase 11 — Question 21: weighted performance rankings

## Business problem and exact formula

The brief asks for a comprehensive ranking combining batting, bowling and fielding, with these specified weights:

```text
Batting points  = runs × 0.01 + batting average × 0.5 + strike rate × 0.3
Bowling points  = wickets × 2 + (50 − bowling average) × 0.5
                  + (6 − economy rate) × 2
Fielding points = catches × 3 + stumpings × 5
Total points    = batting points + bowling points + fielding points
```

The Word brief contains a stray closing parenthesis in its bowling line. The query balances the expression as shown while preserving every coefficient and term. No additional weights, normalization, clamp or top-N cutoff are invented. Rank all eligible players within each exact format because the question says top performers without supplying a number of places.

## Statistical definitions and missing-data rules before SQL

Use latest committed career statistics for one source. Batting average = runs/dismissals, strike rate = 100×runs/balls faced, bowling average = runs conceded/wickets, and economy = 6×runs conceded/legal balls. Positive known denominators permit recalculation; unknown denominators permit their separately supplied reported ratios as implemented. Zero denominators make ratios undefined and are not replaced with numeric provider placeholders.

A complete weighted score requires known runs, wickets, catches, stumpings and all four defined ratios. Missing data never becomes zero. An unknown raw total needed by the formula remains disqualifying even when some reported ratio exists. For example, a reported bowling average cannot replace an unknown wickets total in the wickets×2 term. Unknown conceded runs with positive known denominators cannot be silently filled from a ratio.

This is **complete-case ranking**, not a ranking of every stored profile. Pure batting specialists with zero wickets have an undefined bowling average under the supplied formula and cannot receive a defensible full score without an additional scoring convention. Similarly no-dismissal careers can lack a defined batting average. The query leaves them unranked rather than awarding favorable points through invented zero averages. This coverage/selection effect must be visible when interpreting results.

Bowling points can be negative when averages/economies exceed the formula's baselines. Preserve those values exactly; no floor at zero is specified. The score mixes career-volume and rate metrics, so it is a requested heuristic, not a validated measure of talent. Rankings are within format, not between formats, and no causal/predictive claim follows.

## Concepts, tables and relationships

Use staged CTEs, CASE and NULL checks, real arithmetic, named score components, a window function DENSE_RANK with PARTITION BY, and final display rounding.

`v_latest_career` selects the latest committed row for each player/format/source by fetched_at and batch-ID tie-breaker, excluding deleted profiles and failed/pending batches. `formats` supplies exact category codes, `sources` selects a single origin, and `players` supplies the display name. Career batting, bowling and fielding must already share a consistent scope; this query does not combine unrelated snapshots or derive missing fielding totals from the limited scorecard history.

## Query logic and execution strategy before SQL

Derive metrics, require complete formula inputs, compute each component, sum the raw components, and dense-rank totals descending within format_id. Only then round displayed components/totals. Equal raw scores share ranks such as 1,2,2,3. Player IDs stabilize display order within a tie but do not break the shared rank.

Use exact stored formats separately, including provider-specific INTERNATIONAL_T20 if fully populated. Do not relabel it as T20I. Same-named players and source-scoped identities are not merged. There is no date, minimum-career-length or format subset restriction in this question.

The optimizer may inline portions of the metric/score CTEs and must process a window order; its actual measured plan appears below.

## SQL query

```sql
-- Q21: Complete-case weighted career score, ranked within each source format.
WITH career_metrics AS (
    SELECT c.player_id, c.format_id, f.code AS cricket_format,
        c.runs, c.wickets, c.catches, c.stumpings,
        CASE WHEN c.dismissals > 0 THEN 1.0 * c.runs / c.dismissals
             WHEN c.dismissals IS NULL THEN c.reported_batting_average
        END AS batting_average,
        CASE WHEN c.balls_faced > 0 THEN 100.0 * c.runs / c.balls_faced
             WHEN c.balls_faced IS NULL THEN c.reported_strike_rate
        END AS strike_rate,
        CASE WHEN c.wickets > 0 THEN 1.0 * c.runs_conceded / c.wickets
             WHEN c.wickets IS NULL THEN c.reported_bowling_average
        END AS bowling_average,
        CASE WHEN c.legal_balls_bowled > 0
                  THEN 6.0 * c.runs_conceded / c.legal_balls_bowled
             WHEN c.legal_balls_bowled IS NULL THEN c.reported_economy
        END AS economy_rate
    FROM v_latest_career AS c
    JOIN formats AS f ON f.format_id = c.format_id
    JOIN sources AS s ON s.source_id = c.source_id
    WHERE s.name = :source_name AND c.scope = 'career'
), component_points AS (
    SELECT player_id, format_id, cricket_format,
        runs * 0.01 + batting_average * 0.5 + strike_rate * 0.3 AS batting_points,
        wickets * 2.0 + (50.0 - bowling_average) * 0.5
            + (6.0 - economy_rate) * 2.0 AS bowling_points,
        catches * 3.0 + stumpings * 5.0 AS fielding_points
    FROM career_metrics
    WHERE runs IS NOT NULL AND wickets IS NOT NULL
      AND catches IS NOT NULL AND stumpings IS NOT NULL
      AND batting_average IS NOT NULL AND strike_rate IS NOT NULL
      AND bowling_average IS NOT NULL AND economy_rate IS NOT NULL
), scored_players AS (
    SELECT *, batting_points + bowling_points + fielding_points AS total_points
    FROM component_points
), ranked_players AS (
    SELECT *, DENSE_RANK() OVER (
        PARTITION BY format_id ORDER BY total_points DESC
    ) AS performance_rank
    FROM scored_players
)
SELECT r.cricket_format, r.performance_rank, p.full_name AS player_name,
    ROUND(r.batting_points, 2) AS batting_points,
    ROUND(r.bowling_points, 2) AS bowling_points,
    ROUND(r.fielding_points, 2) AS fielding_points,
    ROUND(r.total_points, 2) AS total_points
FROM ranked_players AS r
JOIN players AS p ON p.player_id = r.player_id
ORDER BY r.cricket_format ASC, r.performance_rank ASC, p.player_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states complete-case scoring from one source with separate format ranks. |
| 2 | Begin a CTE that derives the required career metrics. |
| 3 | Keep player/format identities and the exact format code. |
| 4 | Keep the raw run/wicket/catch/stumping totals required by the formula. |
| 5 | Calculate batting average from runs and positive dismissals. |
| 6 | For an unknown dismissal denominator, retain a supplied reported batting average. |
| 7 | Name the nullable batting-average metric. |
| 8 | Calculate strike rate as runs per hundred balls when the denominator is positive. |
| 9 | Allow a supplied reported strike rate only for an unknown ball denominator. |
| 10 | Name the nullable strike-rate metric. |
| 11 | Calculate bowling average as conceded runs per positive wicket count. |
| 12 | Preserve a reported bowling average if its denominator is unknown; unknown wicket totals still fail complete-score eligibility later. |
| 13 | Name bowling average. |
| 14 | Check that the legal-ball denominator is positive. |
| 15 | Calculate conceded runs per six legal balls. |
| 16 | Allow reported economy only when the ball denominator is unknown. |
| 17 | Name the nullable economy metric. |
| 18 | Read latest committed career snapshots; the view excludes deleted players. |
| 19 | Resolve the exact cricket format. |
| 20 | Resolve the source identity. |
| 21 | Keep only the bound selected source and career scope. |
| 22 | Begin the component-points CTE. |
| 23 | Carry identity and format context. |
| 24 | Apply the specified batting weights without intermediate rounding. |
| 25 | Apply wickets and bowling-average weights. |
| 26 | Apply the economy weight and name the combined bowling component. |
| 27 | Apply catch and stumping weights. |
| 28 | Read the derived metrics. |
| 29 | Require known runs and wickets; unknown totals cannot supply weighted points. |
| 30 | Require known fielding counts; genuine zeros remain valid. |
| 31 | Require defined batting average and strike rate. |
| 32 | Require defined bowling average and economy. |
| 33 | Begin the total-score CTE. |
| 34 | Add the three unrounded components. |
| 35 | Read complete component rows. |
| 36 | Begin the rank CTE. |
| 37 | Use DENSE_RANK so equal unrounded totals share a rank without gaps. |
| 38 | Start each exact format at rank one and order its raw totals descending. |
| 39 | Name the rank. |
| 40 | Read total-score rows. |
| 41 | End the final CTE. |
| 42 | Return format, rank and player name. |
| 43 | Round batting points only for display. |
| 44 | Round bowling points only for display. |
| 45 | Round fielding points only for display. |
| 46 | Round total points only for display; ranking already used the raw value. |
| 47 | Read ranked rows. |
| 48 | Resolve displayed player name by identity. |
| 49 | Order formats, their ranks and stable player-ID ties without changing rank values. |

## Running it and exact arithmetic example

Load `sql/queries/q21_weighted_performance_rank.sql` and execute SQLAlchemy `text(query)` in an existing read transaction. Bind source_name to `Synthetic training fixture` or `cricketapilive-cricbuzz-cricket/v2/provider`. Missing or hostile-looking input does not become SQL and yields no rankings.

An isolated test fixture with 1,000 runs, batting average 50, strike rate 100, 50 wickets, bowling average 30, economy 5, ten catches and two stumpings yields:

```text
Batting = 10 + 25 + 30 = 65
Bowling = 100 + 10 + 2 = 112
Fielding = 30 + 10 = 40
Total = 217
```

The unchanged fictional sample returns **36 player-format rows**: twelve players in each of ODI, T20I and TEST. Sample Player 12 leads each synthetic format:

| Batting points | Bowling points | Fielding points | Total points |
| ---: | ---: | ---: | ---: |
| 92.84 | 200.66 | 66.00 | 359.50 |

Component display values are rounded; the total is calculated from unrounded components and may not always equal the sum of rounded display values. Repeated sample values across formats reflect synthetic seed simplifications, not real professional rankings.

Live output is empty. All three latest career rows lack catches/stumpings; some also lack a defined bowling average due to zero wickets. Zero output is unmet complete-score coverage, not evidence of zero player performance. No fielding count was fabricated to manufacture a ranking.

Complete outputs, fielding-coverage diagnostics and plans are in `11_q21_result.json`. Working databases were read without changes, and no API request was made.

## Actual SQLite execution plan and optimization

Both datasets use co-routines for the ranked/window query, the unique source-name index, career format/player index access and primary-key batch/active-player/format lookups. Latest-snapshot checks use source/fetch-time and snapshot-identity indexes. Temporary B-trees support the window order and final display order. No promise is made that every named CTE is physically materialized.

Keep source scope and input-completeness checks before ranking. Do not join raw innings/fielding rows to career totals, which can multiply counts and mix scopes. DENSE_RANK partitions by stable format ID rather than merging labels. Rounding before the window would create false ties, so rank the raw score.

Do not COALESCE undefined averages or absent fielding to zero: that both changes the requested score and can reward missing bowling evidence. Do not compare mixed-format ranks as if the scoring scale were empirically normalized. Existing identity/source/latest-row indexes support input selection; a raw-score index cannot precompute a score that depends on the latest snapshot and derived ratios.

No new schema or index change was justified. Larger workloads may warrant benchmarking a versioned score projection, but it must preserve input lineage, formula version and refresh consistency. The window-function execution is verified on the current SQLite runtime; PostgreSQL/MySQL execution is not claimed.

## Verification and checkpoint

The full suite passes **340 tests**; lint, formatting and whitespace checks pass. Eleven focused checks cover exact components/total; per-format dense ties; NULL fielding versus known zeros; all four zero-denominator cases; negative points; latest-source isolation and deleted profiles; reported ratios for unknown denominators; and rounding not creating rank ties. All test modifications occur only in isolated temporary databases.

Question 21 is complete. Question 22 has not been implemented. Say **NEXT** to proceed to Question 22.
