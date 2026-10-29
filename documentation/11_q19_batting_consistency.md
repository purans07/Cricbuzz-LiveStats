# Phase 11 — Question 19: consistency of innings scoring

## Business problem

The exact brief asks: “Determine which batsmen are most consistent in their scoring. Calculate the average runs scored and the standard deviation of runs for each player. Only include players who have faced at least 10 balls per innings and played since 2022. A lower standard deviation indicates more consistent performance.”

## Statistical definitions before SQL

Analyze individual ordinary-innings scores, not summed match totals. Each included innings must have at least ten known balls faced, a known runs value, and a known UTC match start on/after 2022-01-01. A Test match with two eligible innings contributes two observations. An ineligible shorter innings is excluded rather than disqualifying that player’s otherwise eligible scores.

Use **population** standard deviation to describe the full stored eligible score population:

```text
mean = SUM(scores) / N
population variance = SUM((score - mean)^2) / N
population standard deviation = SQRT(population variance)
```

This is not sample standard deviation, whose denominator is N-1 for estimating a larger population. For scores 10, 20, 30, the mean is 20 and population deviation is sqrt(200/3) ≈ 8.16; sample deviation would be 10. The brief does not choose a convention, so this lesson records the descriptive population convention explicitly.

No minimum innings count beyond one is specified. A singleton population has deviation zero, so eligible_innings is returned prominently. That is not reliable evidence of consistent future performance. Consistently low scoring can also have low deviation; read average score and sample size together. No claim about ability, prediction or a worldwide consistency ranking follows from these descriptive values.

Unknown runs/balls/dates cannot establish an eligible numerical observation and are excluded rather than filled with zero. The results describe the available known-score subset, not complete player history. Known zero runs with at least ten faced balls is an eligible score.

## Concepts, tables and relationships

Use CTEs, WHERE range/innings filters, COUNT, AVG, a player-keyed join for the second pass, squared deviations, SQRT, ROUND and stable ordering.

`v_active_batting` supplies undeleted batting for active players and excludes super overs. `matches` supplies starts_at. `players` supplies display names; no role='Batsman' restriction is added, since all-rounders and keepers can have batting observations. Match status is not restricted to completed: latest live-innings observations can qualify and remain provisional.

SQLite lacks a universally available built-in STDDEV aggregate, so calculate the population statistic explicitly. The current Python SQLite build is **3.50.2** and `SELECT SQRT(4.0)` was verified to return 2.0. Other SQLite distributions must provide the math function; this is an executable dependency, not proof that every SQLite build enables it. PostgreSQL/MySQL syntax/execution is not verified here.

## Query logic and planned execution

Filter eligible known innings scores and cast runs to real arithmetic. Compute each player's unrounded mean and observation count. Join those scores to that same player's mean, average their squared deviations, then take the square root for display.

The centered two-pass calculation avoids the catastrophic cancellation possible in AVG(x*x)-AVG(x)*AVG(x), especially when scores share a large common offset. It also prevents integer squaring overflow by converting runs before multiplication. Floating-point arithmetic still has finite precision; no exact-arithmetic guarantee is claimed for arbitrarily large integers.

Sort by the unrounded variance ascending. Square root is monotonic for nonnegative variance, so this produces the same consistency order as unrounded standard deviation. Higher unrounded average breaks equal-variance ties, then player ID gives stable ordering. Do not rank by already rounded displayed deviations.

Logically this performs filtered score selection, mean aggregation, player-keyed centered variance and final name lookup/order. The physical plan is measured below.

## SQL query

```sql
-- Q19: Population standard deviation of known qualifying innings scores (SQLite).
WITH eligible_innings AS (
    SELECT b.player_id, 1.0 * b.runs AS runs
    FROM v_active_batting AS b
    JOIN matches AS m ON m.match_id = b.match_id
    WHERE m.starts_at >= '2022-01-01T00:00:00Z'
      AND b.balls_faced >= 10
      AND b.runs IS NOT NULL
), player_means AS (
    SELECT player_id, COUNT(*) AS eligible_innings,
           AVG(runs) AS average_runs
    FROM eligible_innings
    GROUP BY player_id
), player_variances AS (
    SELECT a.player_id, a.eligible_innings, a.average_runs,
           AVG((e.runs - a.average_runs) * (e.runs - a.average_runs))
               AS population_variance
    FROM player_means AS a
    JOIN eligible_innings AS e ON e.player_id = a.player_id
    GROUP BY a.player_id, a.eligible_innings, a.average_runs
)
SELECT
    p.full_name AS player_name,
    v.eligible_innings,
    ROUND(v.average_runs, 2) AS average_runs,
    ROUND(SQRT(v.population_variance), 2) AS standard_deviation_runs
FROM player_variances AS v
JOIN players AS p ON p.player_id = v.player_id
ORDER BY v.population_variance ASC, v.average_runs DESC, p.player_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment defines population deviation of qualifying known innings scores and the SQLite implementation. |
| 2 | Create a CTE for the eligible innings population. |
| 3 | Keep player identity and convert runs to real arithmetic before later squaring. |
| 4 | Read active ordinary-innings batting. |
| 5 | Resolve the match start time. |
| 6 | Include matches starting from 1 January 2022 UTC onward. |
| 7 | Require at least ten known balls faced in this individual innings. |
| 8 | Only known scores can enter numerical descriptive statistics. |
| 9 | Begin the player-mean CTE. |
| 10 | Count eligible innings for each player. |
| 11 | Compute the unrounded mean innings score. |
| 12 | Read the eligible score population. |
| 13 | Group by player identity. |
| 14 | Begin the population-variance CTE. |
| 15 | Keep identity, innings count and unrounded mean. |
| 16 | Average squared deviations of eligible scores from that mean. |
| 17 | Name the population variance. |
| 18 | Read the player means. |
| 19 | Join each player’s eligible scores back to their own mean. |
| 20 | Keep each player’s variance group separate. |
| 21 | End the variance CTE. |
| 22 | Begin the output projection. |
| 23 | Return the player name. |
| 24 | Return the innings sample count so evidence size is visible. |
| 25 | Round the displayed average score to two decimals. |
| 26 | Take the square root of population variance and round the displayed deviation. |
| 27 | Read the calculated player statistics. |
| 28 | Resolve the displayed name by identity. |
| 29 | Sort by unrounded variance ascending, then higher mean, then stable player ID. |

## Running it and observed output

Load `sql/queries/q19_batting_consistency.sql` and execute SQLAlchemy `text(query)` in an existing read transaction. There are no parameters, format restrictions, top-N limit or upper analysis-time cutoff. Year eligibility uses match start, not completion or local display date. Source-scoped identities stay separate even when names match.

The fictional sample returns 12 players. Its first three rows are:

| Player | Eligible innings | Mean score | Population deviation |
| --- | ---: | ---: | ---: |
| Sample Player 09 | 96 | 65.31 | 29.35 |
| Sample Player 10 | 96 | 65.38 | 29.41 |
| Sample Player 01 | 96 | 67.00 | 29.53 |

These scores are simplified fictional training data. Live output contains 16 players, 11 of whom have only one eligible innings and deviation zero. Bavuma's single eligible score is 179, for example; his zero deviation does not establish consistency. The imported data covers one match, not a representative career population. The remaining players have at most two observed eligible innings.

Full outputs, exact SQLite version and measured plans are in `11_q19_result.json`. Working databases were read without changes, and no API request was used.

## Actual SQLite execution plan and optimization

Both databases use co-routines for player means and variances. The initial batting access uses `idx_batting_player_match`, with player/innings/match primary-key checks. The centered second pass looks up batting by player through that index and reapplies the eligible view/metadata checks. Temporary B-trees support variance grouping and final ordering.

The CTEs express logical steps but do not force a particular materialization strategy. The actual plan does not show a start-date range-index lookup; dates are still filtered after match identity resolution. The exact plan is retained rather than asserting unused index support.

Keep the date comparison directly on canonical starts_at and the per-innings ball condition directly on balls_faced. Do not join career totals or match memberships into an innings distribution, average rounded means, or merge same-named players. Existing primary keys prevent duplicate individual innings rows.

No new index or schema change was introduced. At larger scale, benchmark whether materializing the eligible score set once reduces repeated active-view evaluation, accounting for temporary storage costs. A score-only index does not replace player/date/ball eligibility or the two-stage statistic.

## Verification and checkpoint

The full suite passes **322 tests**; lint, formatting and whitespace checks pass. Six focused tests cover known population mean/deviation versus sample deviation; exact 2022 and ten-ball boundaries; NULL exclusion and known zero; singleton behavior; two innings in one match remaining distinct; deleted profiles/performances and super overs; equal-named identity/rank handling; and large common score offsets without cancellation. The large-offset test values are artificial numerical boundary cases, not cricket records. All test changes occur in isolated temporary databases.

Question 19 is complete. Question 20 has not been implemented. Say **NEXT** to proceed to Question 20.
