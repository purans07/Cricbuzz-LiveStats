# Phase 11 — Question 18: economical limited-overs bowlers

## Business problem

The exact brief asks: “Find the most economical bowlers in limited-overs cricket (ODI and T20 formats). Calculate each bowler's overall economy rate and total wickets taken. Only consider bowlers who have bowled in at least 10 matches and bowled at least 2 overs per match on average.” This ranks eligible bowling populations by runs conceded per over.

## Definitions and statistical method before SQL

Include format families ODI and T20. Unlike questions that explicitly require verified T20I, this question asks broadly for T20 formats, so stored domestic/league T20, IPL and INTERNATIONAL_T20 can be included alongside T20I. Exact international eligibility is not inferred from the family. Test and OTHER formats, including Hundred classifications, are excluded.

The calculation pools eligible ODI/T20 matches across formats per player; it does not require ten ODI and ten T20 games separately. Overall economy = **6 × total runs conceded / total legal balls**. This is a ball-weighted pooled rate, not an arithmetic mean of match economies. Question 14 explicitly used a mean match economy; this question's “overall” calls for pooled numerators and denominators.

Require at least ten evidenced bowling matches, and average workload >=12 legal balls per match. This is an average requirement, not a two-over minimum in every match. For example, five one-over matches plus five three-over matches meet a two-over average. Apply the eligibility comparison in integer balls before rounding display values.

A bowled match requires positive known evidence in at least one included bowling row: legal balls, conceded runs or bowling wickets. All-zero placeholder lines do not count. A zero-legal-ball appearance with positive conceded runs/wickets can represent illegal-delivery bowling and is not automatically discarded. A wholly unknown line cannot itself establish bowling participation. Missing entire rows still limit coverage.

All included ball counts must be known to establish the mean-overs requirement. Unknown runs preserve an eligible row with NULL economy, shown after known rates rather than ranked as zero. Unknown wickets produce a NULL total, not a partial sum. Known zero remains a genuine zero; the brief imposes no minimum wicket count.

## Concepts, tables and relationships

Use two CTEs for match-level and player-level aggregation, SUM, COUNT, CASE completeness checks, HAVING for workload thresholds, format joins, real division, ROUND and ranking order.

`v_active_bowling` supplies bowling rows for active players, excluding deleted performances and super overs. `matches.format_id` references `formats`; family identifies the requested limited-overs groups. `players` supplies names. Actual bowling records determine the population; a profile need not have role='Bowler', since all-rounders can qualify.

## Query logic and planned execution

Combine ordinary innings within each limited-overs match. Keep evidenced bowled matches and preserve unknown totals. Then aggregate by player, requiring ten matches and known average workload of at least two overs. Compute the pooled economy and rank known values ascending, keeping unknown metrics visibly unrankable at the end. There is no arbitrary top-N limit or extra economy cutoff in the brief.

The match grain prevents extra innings from inflating the ten-match count. No completed-only or date restriction is specified: figures may include live/abandoned match observations if bowling is evidenced; they are not guaranteed final figures. Different source-scoped identities remain separate, even if names match.

The expected physical work is active bowling access, format filtering, match aggregation, player aggregation and ranking. SQLite's measured behavior appears below.

## SQL query

```sql
-- Q18: Pooled economy across ODI/T20 matches with sufficient bowling exposure.
WITH match_bowling AS (
    SELECT b.player_id, b.match_id,
        CASE WHEN COUNT(*) = COUNT(b.legal_balls)
             THEN SUM(b.legal_balls) END AS match_balls,
        CASE WHEN COUNT(*) = COUNT(b.runs_conceded)
             THEN SUM(b.runs_conceded) END AS match_runs,
        CASE WHEN COUNT(*) = COUNT(b.wickets)
             THEN SUM(b.wickets) END AS match_wickets
    FROM v_active_bowling AS b
    JOIN matches AS m ON m.match_id = b.match_id
    JOIN formats AS f ON f.format_id = m.format_id
    WHERE f.family IN ('ODI', 'T20')
    GROUP BY b.player_id, b.match_id
    HAVING SUM(b.legal_balls) > 0 OR SUM(b.runs_conceded) > 0
           OR SUM(b.wickets) > 0
), qualified_bowlers AS (
    SELECT player_id, COUNT(*) AS matches_bowled,
        SUM(match_balls) AS total_balls,
        CASE WHEN COUNT(*) = COUNT(match_runs)
             THEN SUM(match_runs) END AS total_runs,
        CASE WHEN COUNT(*) = COUNT(match_wickets)
             THEN SUM(match_wickets) END AS total_wickets
    FROM match_bowling
    GROUP BY player_id
    HAVING COUNT(*) >= 10
       AND COUNT(*) = COUNT(match_balls)
       AND SUM(match_balls) >= 12 * COUNT(*)
)
SELECT
    p.full_name AS player_name,
    ROUND(6.0 * q.total_runs / q.total_balls, 2) AS overall_economy_rate,
    q.total_wickets,
    q.matches_bowled,
    ROUND(q.total_balls / (6.0 * q.matches_bowled), 2) AS average_overs_per_match
FROM qualified_bowlers AS q
JOIN players AS p ON p.player_id = q.player_id
ORDER BY (q.total_runs IS NULL) ASC,
         6.0 * q.total_runs / q.total_balls ASC, p.player_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment defines the limited-overs exposure and pooled-rate scope. |
| 2 | Create the per-player/match bowling CTE. |
| 3 | Keep player and match identity. |
| 4 | Check whether all included legal-ball counts are known. |
| 5 | Sum match legal balls only when complete. |
| 6 | Check whether all included conceded-run values are known. |
| 7 | Sum conceded runs only when complete. |
| 8 | Check whether all included wickets are known. |
| 9 | Sum wickets only when complete. |
| 10 | Read undeleted ordinary-innings bowling for active players. |
| 11 | Resolve each bowling row’s match. |
| 12 | Resolve the match format. |
| 13 | Include ODI and T20 format families; exclude Test and OTHER. |
| 14 | Produce one unit per player/match. |
| 15 | Require positive known ball or conceded-run evidence that the player bowled. |
| 16 | Also accept positive known bowling-wicket evidence; all-zero placeholders do not establish a bowled match. |
| 17 | Begin the qualified-player CTE. |
| 18 | Count the player’s evidenced bowling matches. |
| 19 | Sum their match ball totals. |
| 20 | Require conceded runs to be known across every included match. |
| 21 | Sum those run totals only when complete. |
| 22 | Require wickets to be known across every included match. |
| 23 | Sum those wicket totals only when complete. |
| 24 | Read the player-match bowling units. |
| 25 | Group by player identity. |
| 26 | Require at least ten bowled matches. |
| 27 | Require known ball totals for all included matches. |
| 28 | Require total legal balls >= 12 times match count: at least two overs per match on average. |
| 29 | End qualified-player selection. |
| 30 | Begin displayed output fields. |
| 31 | Resolve the player name. |
| 32 | Compute pooled runs per six legal balls and round to two decimals. |
| 33 | Return the nullable total wickets. |
| 34 | Return the match count so eligibility is visible. |
| 35 | Return arithmetic average overs as a decimal quantity for workload auditing. |
| 36 | Read qualified player totals. |
| 37 | Look up player name by primary-key identity. |
| 38 | Place unknown economy totals after known rates. |
| 39 | Sort known bowlers by the unrounded pooled economy, lowest first; player ID resolves exact ties. |

## Running it and observed outputs

Load `sql/queries/q18_limited_overs_economy.sql` and execute SQLAlchemy `text(query)` in an existing read transaction. No parameters are required. The output includes match count and average workload to make threshold verification visible.

The fictional sample returns 12 eligible bowlers from 48 stored limited-overs matches. Its first three rows are:

| Player | Pooled economy | Wickets | Matches bowled | Mean overs/match |
| --- | ---: | ---: | ---: | ---: |
| Sample Player 03 | 8.93 | 48 | 48 | 7.53 |
| Sample Player 01 | 8.96 | 48 | 48 | 7.57 |
| Sample Player 06 | 8.99 | 0 | 48 | 7.43 |

Average overs here is a mathematical decimal mean, not cricket O.B notation: 7.53 is not “seven overs and 53 balls.” Eligibility uses exact ball totals, and ranking uses unrounded economy; rounding the display cannot reverse very close rates.

These simplified synthetic figures are not real professional rankings. Live output is empty: detailed bowling currently comes from a Test match, and there are no stored ODI/T20 bowling matches to establish ten appearances. This does not imply no real bowler qualifies.

Complete outputs, format-scoped coverage and plans are in `11_q18_result.json`. Working databases were read without modification. No API request was made.

## Actual SQLite plan and optimization

Both working datasets use co-routines for the match/player aggregates. SQLite scans active bowling through `idx_bowling_player_match`, resolves player/innings/match/format metadata by primary keys and applies the family filter. It scans the match units and uses a temporary B-tree for the player aggregate, then looks up display names and sorts final rates.

Keep the average-workload condition as SUM(balls) >=12×COUNT(matches), not a rounded average >=2. Do not filter each innings or match at two overs, because the brief's requirement is average exposure. Do not count all match-player appearances as games bowled or all-zero roster placeholders as positive bowling evidence.

Pooled economy must use total runs divided by total balls; AVG of match economy changes its weights. Compare formats through family classification rather than substring matching names. Preserve the active-view deletion/super-over policy. Completeness checks are necessary because SQL SUM otherwise ignores NULL.

No index or schema change was added. With larger history, benchmark format-first versus bowling-first access and whether a maintained per-match aggregate is justified. A runs-only index cannot establish match workload, latest coverage or a pooled ratio. The observed SQLite plan is not PostgreSQL/MySQL verification.

## Verification and checkpoint

The full suite passes **316 tests**; lint, formatting and whitespace checks pass. Seven focused tests cover mixed ODI/T20 pooling versus an arithmetic mean; ten-match eligibility and exact 12-ball average boundary; shorter individual spells qualifying on average; extra innings not becoming matches; Test/zero-placeholder exclusion; unknown totals/ball counts; deleted rows/players and super overs; and lowest-economy ordering for distinct equal-named bowlers. Test changes occur only in isolated temporary databases.

Question 18 is complete. Question 19 has not been implemented. Say **NEXT** to proceed to Question 19.
