# Phase 11 — Question 23: recent player form and momentum

## Assignment before SQL

Analyze each player's last ten batting performances: average runs over the last five versus last ten matches, strike-rate trends, scores above 50, a standard-deviation consistency score, and Excellent/Good/Average/Poor Form categories.

## Definitions and business decisions before SQL

The brief switches from performances to matches. Use **one batting performance per player/match**, adding all stored active ordinary innings in that match. A Test with two innings occupies one position in the ten-match window. A score above 50 here means a **match total strictly greater than 50**, not an innings half-century; 50 itself does not count. This explicit interpretation keeps all metrics at the requested match grain. Average runs means runs per batting match, not runs per dismissal.

Use completed matches with a known UTC start before the bound `as_of_utc`, newest starts first. A higher match ID breaks equal-date ties deterministically; it is not evidence of actual finishing order. Use each player's last ten qualifying matches, then take the newest five within those ten. Players who did not bat do not acquire zero scores. Scheduled/live matches, super overs, deleted batting rows and deleted profiles are excluded. Players without eligible batting records do not appear. A recorded zero is valid. Keep unknown scores in their actual window position instead of skipping them to pull in older known results.

All formats are combined for one result per player, as the brief specifies no format partition. This can substantially affect interpretation: Test match totals and T20 totals have different scales, as do their strike rates. These teaching labels are unsuitable for cross-format talent comparisons. A later product can expose format-specific windows explicitly.

Only require ten observed completed batting matches for a category. Short histories still show available metrics and actual sample counts, with a NULL category and `insufficient_history`. Unknown required values yield `incomplete_metrics`; NULL never means Poor Form. A completed match may have partially imported innings; SQL can detect NULL cells, but cannot prove that an absent innings or an unimported match exists. These are **stored-history windows**, not verified full career histories.

The cutoff controls scheduled starts on the current saved database, not historical database snapshots. A match completed after an earlier cutoff could still be included when it started before that cutoff. For true point-in-time evaluation, require known completion times plus versioned observations; this lesson does not claim that capability. Sample cutoff is 2026-10-01T00:00:00Z; live cutoff is the saved capture timestamp 2026-10-22T07:52:06Z.

## Metrics and teaching thresholds before SQL

- Last-five/ten run averages use arithmetic mean of match totals. Missing any contributing runs makes that window's average NULL.
- Strike rate = 100 × total runs / total balls faced within that window. It is a pooled rate, not the mean of match rates. All contributing runs and balls must be known, and total balls must be positive. A zero-ball match can coexist with a valid pooled denominator; a wholly zero-ball window has no defined strike rate.
- Runs momentum = last-five average − last-ten average. Strike-rate change = last-five rate − last-ten rate, in percentage points. The windows overlap, so this is a recent-versus-baseline comparison rather than independent-period evidence or a fitted trend.
- Population standard deviation = square root of the mean squared deviation from the last-ten mean. Calculate it in two passes to avoid subtracting large squared totals. One known observation has deviation zero, but still cannot receive a category.
- Consistency score = 100 / (1 + standard deviation / 25). The 25-run scale is a transparent teaching choice. Scores approach zero as variability grows and equal 100 for constant scores. Constant zero scores can be consistent while remaining Poor Form; consistency is not quality.

The brief supplies no thresholds or score formula. The following are **project heuristics**, not official cricket standards or validated predictions. Apply rows top to bottom, using unrounded metrics. Every classified player must have ten matches and complete required metrics.

| Category | Last-five average | Runs momentum | Strike-rate change | Consistency | Last-five match totals >50 |
| --- | --- | --- | --- | --- | --- |
| Excellent Form | ≥50 | ≥0 | ≥0 | ≥50 | ≥2 |
| Good Form | ≥35 | ≥−5 | ≥−10 | ≥40 | ≥1 |
| Average Form | ≥20 | unrestricted | unrestricted | ≥25 | unrestricted |
| Poor Form | Remaining complete ten-match cases | | | | |

For example, ten constant 60-run scores qualify as Excellent; nine 40s followed by 60 qualify as Good; constant 20s are Average; constant zeros are Poor. High averages with volatile scores may receive Average under this deliberately strict consistency rule. The threshold table makes that tradeoff reviewable rather than implying an empirical conclusion.

## Concepts, tables and relationships before SQL

CTEs stage match totals, ROW_NUMBER ordering, conditional aggregation, population variance, derived indicators and CASE classification. `v_active_batting` joins active players and ordinary innings, filtering tombstones and super overs. Join `matches` by match ID for dates/status, and `players` by stable player ID for output labels. Names never identify or merge players. No career snapshot, fielding, bowling, toss or API table is needed.

Aggregate innings before assigning row numbers so multi-innings Tests cannot consume multiple window positions. Rank all eligible matches, limit to ten, derive both window summaries, compute dispersion using the same last-ten mean, then classify raw metrics before rounding the display. CASE/COUNT guards prevent AVG and SUM from silently ignoring unknown values. Missing balls do not hide otherwise known run averages; they do withhold the category.

## SQL

```sql
-- Q23: Match-based recent batting form across all formats; explicit UTC cutoff.
WITH match_scores AS (
    SELECT b.player_id,b.match_id,m.starts_at,
           CASE WHEN COUNT(*)=COUNT(b.runs) THEN SUM(b.runs) END AS runs,
           CASE WHEN COUNT(*)=COUNT(b.balls_faced) THEN SUM(b.balls_faced) END AS balls
    FROM v_active_batting b
    JOIN matches m ON m.match_id=b.match_id
    WHERE m.status='completed' AND m.starts_at < :as_of_utc
    GROUP BY b.player_id,b.match_id,m.starts_at
), ordered AS (
    SELECT *,ROW_NUMBER() OVER (
        PARTITION BY player_id ORDER BY starts_at DESC,match_id DESC
    ) AS recency
    FROM match_scores
), recent AS (
    SELECT * FROM ordered WHERE recency<=10
), metrics AS (
    SELECT player_id,COUNT(*) AS matches_last_10,
           SUM(recency<=5) AS matches_last_5,
           CASE WHEN COUNT(runs)=COUNT(*) THEN AVG(runs) END AS average_runs_last_10,
           CASE WHEN COUNT(CASE WHEN recency<=5 THEN runs END)=SUM(recency<=5)
                THEN AVG(CASE WHEN recency<=5 THEN runs END) END AS average_runs_last_5,
           CASE WHEN COUNT(runs)=COUNT(*) AND COUNT(balls)=COUNT(*)
                THEN 100.0*SUM(runs)/NULLIF(SUM(balls),0) END AS strike_rate_last_10,
           CASE WHEN COUNT(CASE WHEN recency<=5 THEN runs END)=SUM(recency<=5)
                     AND COUNT(CASE WHEN recency<=5 THEN balls END)=SUM(recency<=5)
                THEN 100.0*SUM(CASE WHEN recency<=5 THEN runs END)
                     /NULLIF(SUM(CASE WHEN recency<=5 THEN balls END),0) END AS strike_rate_last_5,
           CASE WHEN COUNT(runs)=COUNT(*) THEN SUM(runs>50) END AS scores_above_50_last_10,
           CASE WHEN COUNT(CASE WHEN recency<=5 THEN runs END)=SUM(recency<=5)
                THEN SUM(CASE WHEN recency<=5 AND runs>50 THEN 1 ELSE 0 END) END AS scores_above_50_last_5
    FROM recent GROUP BY player_id
), dispersion AS (
    SELECT m.*,SQRT(AVG((r.runs-m.average_runs_last_10)
                       *(r.runs-m.average_runs_last_10))) AS standard_deviation_runs
    FROM metrics m JOIN recent r ON r.player_id=m.player_id
    GROUP BY m.player_id
), indicators AS (
    SELECT *,average_runs_last_5-average_runs_last_10 AS runs_momentum,
           strike_rate_last_5-strike_rate_last_10 AS strike_rate_change,
           100.0/(1.0+standard_deviation_runs/25.0) AS consistency_score
    FROM dispersion
)
SELECT p.player_id,p.full_name AS player_name,i.matches_last_5,i.matches_last_10,
       ROUND(i.average_runs_last_5,2) AS average_runs_last_5,
       ROUND(i.average_runs_last_10,2) AS average_runs_last_10,
       ROUND(i.runs_momentum,2) AS runs_momentum,
       ROUND(i.strike_rate_last_5,2) AS strike_rate_last_5,
       ROUND(i.strike_rate_last_10,2) AS strike_rate_last_10,
       ROUND(i.strike_rate_change,2) AS strike_rate_change,
       i.scores_above_50_last_5,i.scores_above_50_last_10,
       ROUND(i.standard_deviation_runs,2) AS standard_deviation_runs,
       ROUND(i.consistency_score,2) AS consistency_score,
       CASE WHEN i.matches_last_10<10 OR i.average_runs_last_10 IS NULL
                      OR i.strike_rate_change IS NULL THEN NULL
            WHEN i.average_runs_last_5>=50 AND i.runs_momentum>=0
                 AND i.strike_rate_change>=0 AND i.consistency_score>=50
                 AND i.scores_above_50_last_5>=2 THEN 'Excellent Form'
            WHEN i.average_runs_last_5>=35 AND i.runs_momentum>=-5
                 AND i.strike_rate_change>=-10 AND i.consistency_score>=40
                 AND i.scores_above_50_last_5>=1 THEN 'Good Form'
            WHEN i.average_runs_last_5>=20 AND i.consistency_score>=25 THEN 'Average Form'
            ELSE 'Poor Form' END AS form_category,
       CASE WHEN i.matches_last_10<10 THEN 'insufficient_history'
            WHEN i.average_runs_last_10 IS NULL OR i.strike_rate_change IS NULL
                 THEN 'incomplete_metrics' ELSE 'classified' END AS coverage_status
FROM indicators i JOIN players p ON p.player_id=i.player_id
ORDER BY p.player_id;
```

## Every SQL line explained

| Line | Explanation |
| --- | --- |
| 1 | Describe scope and explicit cutoff. |
| 2 | Begin one-row-per-player/match totals. |
| 3 | Select player, match and ordering date. |
| 4 | Sum runs only when every contributing innings has known runs. |
| 5 | Sum balls only when every contributing innings has known balls. |
| 6 | Read active ordinary-innings batting rows. |
| 7 | Attach each match's date and status. |
| 8 | Keep completed fixtures strictly before the bound UTC start cutoff. |
| 9 | Collapse innings at player/match grain. |
| 10 | Begin chronological ranking. |
| 11 | Assign a row number to every eligible batting match. |
| 12 | Restart per player and order newest start, then highest match ID. |
| 13 | Name that position recency. |
| 14 | Read match totals. |
| 15 | Begin the recent window. |
| 16 | Keep positions one through ten, including unknown metrics. |
| 17 | Begin window aggregation. |
| 18 | Identify the player and count available recent matches. |
| 19 | Count positions one through five. |
| 20 | Calculate ten-match mean only with complete run totals. |
| 21 | Check run completeness specifically within the newest five. |
| 22 | Calculate the five-match mean once that check passes. |
| 23 | Require known runs and balls throughout the ten-match window. |
| 24 | Compute pooled ten-match strike rate, avoiding a zero denominator. |
| 25 | Check run completeness in the five-match window. |
| 26 | Also check balls completeness in that window. |
| 27 | Start pooled five-match rate using only those runs. |
| 28 | Divide by those balls, guarding zero. |
| 29 | Count strictly above-50 totals only with complete ten-match scores. |
| 30 | Check newest-five score completeness. |
| 31 | Count above-50 match totals among the newest five. |
| 32 | Produce one metrics row per player. |
| 33 | Begin the second pass for score dispersion. |
| 34 | Subtract the ten-match mean from each score. |
| 35 | Square deviations, average them, then take their square root. |
| 36 | Join the metrics to that player's recent scores. |
| 37 | Produce one dispersion row per player. |
| 38 | Begin derived indicators. |
| 39 | Subtract the baseline run average from the recent average. |
| 40 | Subtract the baseline pooled strike rate from the recent rate. |
| 41 | Convert standard deviation to the documented inverse consistency scale. |
| 42 | Read dispersion metrics. |
| 43 | Finish the CTE chain. |
| 44 | Select stable player identity and actual sample counts. |
| 45 | Round the recent run average for display only. |
| 46 | Round the baseline run average. |
| 47 | Round run momentum. |
| 48 | Round recent strike rate. |
| 49 | Round baseline strike rate. |
| 50 | Round strike-rate change. |
| 51 | Display both above-50 counts without rounding. |
| 52 | Round the population standard deviation. |
| 53 | Round the consistency score. |
| 54 | Withhold classification for short history or unknown baseline runs. |
| 55 | Also withhold classification for unknown strike-rate change. |
| 56 | Start the Excellent thresholds on run average and momentum. |
| 57 | Require nondecreasing strike rate and sufficient consistency. |
| 58 | Require two recent above-50 totals to finish Excellent classification. |
| 59 | Otherwise start the Good run-average and momentum thresholds. |
| 60 | Require strike-rate and consistency thresholds for Good. |
| 61 | Require at least one recent above-50 total to finish Good classification. |
| 62 | Otherwise classify sufficient average and consistency as Average. |
| 63 | Label remaining complete-history cases Poor. |
| 64 | Explain missing classification caused by short history. |
| 65 | Check missing metrics after the history check. |
| 66 | Distinguish incomplete metrics from successfully classified records. |
| 67 | Attach player labels to computed indicators. |
| 68 | Use stable player-ID display ordering. |

## Execution and results

Execute the SQL through a read-only connection with a named `as_of_utc` parameter; for example bind the sample timestamp above. Normalize it to the same UTC timestamp format used by `matches.starts_at`. No implicit machine-clock dependency or API request is needed.

The sample database returns 12 fictional players, each with ten batting matches: two Good Form and ten Average Form under the stated heuristic. Sample Player 01 has last-five average 122.40 versus last-ten 108.80, strike rates 161.90 versus 155.43, five versus nine match totals above 50, standard deviation 45.63 and consistency 35.40. Its Average label reflects the consistency threshold despite high recent scores; it is not a claim about a real player.

The live snapshot returns zero rows because no stored completed match has an eligible batting performance. The detailed South Africa/Australia scorecard is still an unfinished match in this snapshot. Empty output does not imply real players lack recent completed batting history. No labels were fabricated from career totals or unfinished scores.

Full rows, bound parameters and actual SQLite plans are saved in [the execution report](11_q23_result.json).

## Actual plan and optimization

```text
CO-ROUTINE dispersion
CO-ROUTINE metrics
MATERIALIZE ordered
CO-ROUTINE (subquery-12)
MATERIALIZE match_scores
SCAN b USING INDEX idx_batting_player_match
SEARCH players USING INTEGER PRIMARY KEY (rowid=?)
SEARCH i USING INTEGER PRIMARY KEY (rowid=?)
SEARCH m USING INTEGER PRIMARY KEY (rowid=?)
USE TEMP B-TREE FOR GROUP BY
SCAN match_scores
USE TEMP B-TREE FOR ORDER BY
SCAN (subquery-12)
SCAN ordered
USE TEMP B-TREE FOR GROUP BY
SCAN m
BLOOM FILTER ON ordered (player_id=?)
SEARCH ordered USING AUTOMATIC PARTIAL COVERING INDEX (player_id=?)
USE TEMP B-TREE FOR GROUP BY
SCAN dispersion
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
USE TEMP B-TREE FOR ORDER BY
```

SQLite uses indexed joins for eligible batting/match records and temporary grouping and ordering structures for aggregation and the recency window, as recorded above. The existing player/match batting index, primary keys and status/date indexes are available; no new schema index is justified by this fixture size. ROW_NUMBER must inspect all qualifying history to select each player's newest ten. Keep expensive dispersion calculations after the ten-row limit. Do not optimize by discarding unknown scores before ranking, averaging strike rates, or ranking innings before combining Test scores.

## Verification and practical limits

Thirteen focused checks cover all four categories, exact population deviation, five/ten windows, strict >50 counting, short histories, missing runs/balls without backfilling, zero denominators, cutoff and status/date filters, tombstones, super overs, deterministic ties, pooled rates and Test match aggregation. Tests use temporary database copies; working sample/live files were read only. Full suite: 359 tests passed, with lint, formatting and whitespace checks passing.

Form categories are illustrative policy choices. Small samples, overlapping windows, incomplete imports, mixed formats and match totals rather than innings scores all limit their interpretation. This is not a forecast, a rating validated against future outcomes, or a complete time series model.

Question 23 is complete. Question 24 awaits NEXT. Phase 11 remains in progress.
