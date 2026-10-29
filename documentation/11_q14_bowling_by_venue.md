# Phase 11 — Question 14: bowling performance by venue

## Business problem

The exact brief asks: “Examine bowling performance at different venues. For bowlers who have played at least 3 matches at the same venue, calculate their average economy rate, total wickets taken, and number of matches played at each venue. Focus on bowlers who bowled at least 4 overs in each match.”

## Definitions before implementation

A qualifying match has at least **24 legal balls** recorded for that player across its ordinary innings. Four overs means 4 × 6 legal balls, not a decimal-overs calculation. Two two-over innings in one Test match can therefore qualify that one match. Innings must not be counted as separate matches.

Require at least three qualifying matches per player/venue. A player's additional short spell at the venue is excluded from the calculation, rather than disqualifying their otherwise eligible three matches. All reported statistics use the same qualifying set. Unknown venues cannot establish a venue group and are excluded.

Interpret “average economy rate” as the arithmetic mean of qualifying **per-match** economy rates. Each match economy is 6 × total runs conceded / total legal balls in that match. This is distinct from a venue-wide pooled economy (6 × all runs / all balls), which weights matches by balls bowled. For match economies 3, 6 and 9, the mean is 6 even when the last match has twice as many balls. No per-match rounding is applied before averaging.

All included innings must have known legal-ball counts to establish the match threshold. A qualifying match with unknown conceded runs has an unknown economy; any such match makes the final venue mean NULL. Unknown wickets similarly make the reported venue wicket total NULL. Known zero runs or wickets remain zero. Missing entire innings cannot be detected from absent rows, so imported coverage still limits completeness.

## Concepts, tables and relationships

Use a CTE, two-stage GROUP BY/HAVING, SUM, AVG, completeness checks using COUNT, CASE and real division.

`v_active_bowling` exposes undeleted bowling performances for active players and ordinary innings. Each bowling row belongs to one player/innings and carries constrained match/team references. `matches` supplies venue_id; `venues` supplies venue name; `players` supplies player name. “Bowler” here means a player with bowling performances, not only profiles with role='Bowler'; all-rounders can qualify too.

## Query logic and planned execution

First combine active bowling rows by player/match/venue. Keep matches with complete known ball counts totaling at least 24. Compute unrounded per-match economy and wicket totals, preserving unknowns. Then aggregate those match rows by player and venue, requiring at least three of them. Count rows at this stage, not innings, and calculate the arithmetic mean and wicket sum with completeness guards.

No completed-only restriction was requested. A live or abandoned match with sufficient recorded ordinary-innings bowling can qualify; its figures are the latest stored partial observation, not a claim of final career statistics. All calculations cover stored match performances rather than independent career snapshots, and API-owned local overrides/tombstones affect the active rows as designed.

The expected physical work is active bowling reads, match lookup, first aggregation, player/venue lookup, second aggregation and sort. Actual SQLite behavior is recorded below.

## SQL query

```sql
-- Q14: Venue bowling over at least three matches with >= 24 legal balls each.
WITH qualifying_matches AS (
    SELECT
        b.player_id,
        b.match_id,
        m.venue_id,
        CASE WHEN COUNT(*) = COUNT(b.runs_conceded)
             THEN 6.0 * SUM(b.runs_conceded) / SUM(b.legal_balls)
        END AS match_economy,
        CASE WHEN COUNT(*) = COUNT(b.wickets)
             THEN SUM(b.wickets)
        END AS match_wickets
    FROM v_active_bowling AS b
    JOIN matches AS m ON m.match_id = b.match_id
    WHERE m.venue_id IS NOT NULL
    GROUP BY b.player_id, b.match_id, m.venue_id
    HAVING COUNT(*) = COUNT(b.legal_balls)
       AND SUM(b.legal_balls) >= 24
)
SELECT
    p.full_name AS player_name,
    v.name AS venue_name,
    CASE WHEN COUNT(*) = COUNT(q.match_economy)
         THEN ROUND(AVG(q.match_economy), 2)
    END AS average_economy_rate,
    CASE WHEN COUNT(*) = COUNT(q.match_wickets)
         THEN SUM(q.match_wickets)
    END AS total_wickets,
    COUNT(*) AS matches_played
FROM qualifying_matches AS q
JOIN players AS p ON p.player_id = q.player_id
JOIN venues AS v ON v.venue_id = q.venue_id
GROUP BY p.player_id, p.full_name, v.venue_id, v.name
HAVING COUNT(*) >= 3
ORDER BY p.full_name ASC, v.name ASC, p.player_id ASC, v.venue_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states both eligibility thresholds: three matches, at least 24 legal balls in each. |
| 2 | Define a CTE with one qualifying player/match/venue row. |
| 3 | Begin the first-stage projection. |
| 4 | Keep the bowler identity. |
| 5 | Keep match identity so several innings cannot become several matches. |
| 6 | Keep the stored venue identity. |
| 7 | Calculate a match economy only if every included bowling row has known conceded runs. |
| 8 | Compute runs conceded per six legal balls across that match’s ordinary innings. |
| 9 | Name that unrounded value match_economy. |
| 10 | Check that wickets are known in every included bowling row. |
| 11 | Sum wickets across ordinary innings of the match. |
| 12 | Name the nullable match total. |
| 13 | Read active bowling, excluding deleted profiles/records and super overs. |
| 14 | Resolve the match and venue link. |
| 15 | Require a known venue identity for venue-specific analysis. |
| 16 | Group bowling rows into one bowler/match/venue unit. |
| 17 | Require every included legal-ball count to be known. |
| 18 | Require total match legal balls to be at least 24 (four overs). |
| 19 | End the qualifying-match CTE. |
| 20 | Begin the player/venue result projection. |
| 21 | Return the player name. |
| 22 | Return the venue name. |
| 23 | Calculate the venue mean only when all qualifying matches have known economy values. |
| 24 | Take the arithmetic mean of the unrounded per-match economies and round once to two decimals. |
| 25 | Name the average-economy output. |
| 26 | Require every qualifying match to have known wickets before returning a total. |
| 27 | Sum the known qualifying-match wicket totals. |
| 28 | Name the venue wicket total. |
| 29 | Count qualifying match rows; each row already represents one distinct match for this player. |
| 30 | Read the qualifying-match rows. |
| 31 | Resolve the displayed player name. |
| 32 | Resolve the displayed venue name. |
| 33 | Group by player and venue identities, preserving different people/grounds with equal names. |
| 34 | Require at least three qualifying matches at this venue. |
| 35 | Sort by player/venue names with identity tie-breakers. |

## Running it and observed results

Load `sql/queries/q14_bowling_by_venue.sql` and execute SQLAlchemy `text(query)` within an existing read transaction. There are no input parameters, date limits, format filters or top-N limits in this question. Distinct player/venue IDs remain separate despite equal names; source-scoped imported identities are not globally deduplicated.

The fictional sample returns **24 player–venue rows** from bowling data covering 72 matches. For example:

| Player | Venue | Mean match economy | Wickets | Qualifying matches |
| --- | --- | ---: | ---: | ---: |
| Sample Player 01 | Sample Ground 1 | 8.92 | 48 | 36 |
| Sample Player 01 | Sample Ground 2 | 8.90 | 48 | 36 |

These simplified synthetic scorecards are training records, not factual professional statistics. Live data returns no qualifying row because detailed bowling has been imported for only one match. An empty result is insufficient history, not evidence that no real bowler qualifies.

Complete outputs, coverage counts and plans are in `11_q14_result.json`. Working databases were read without modification. No API request was made.

## Actual SQLite execution plan

Both working datasets use a co-routine for qualifying_matches. SQLite scans bowling through `idx_bowling_player_match`, expands active-player/ordinary-innings checks using primary keys, and looks up matches by primary key. Temporary B-trees support the first match-level GROUP BY and the second player/venue GROUP BY. Player/venue names use primary-key lookups, followed by a final ordering sort.

This is the observed current SQLite plan, not PostgreSQL/MySQL verification or a claim that the aggregates avoid scanning eligible performances.

## Optimization and common mistakes

Aggregate innings before applying match-count thresholds. COUNT(DISTINCT match_id) alone at venue level does not enforce four overs in each counted match. Do not filter each individual innings with legal_balls >= 24: that would wrongly exclude two shorter innings that together meet the per-match minimum.

Use integer legal balls and real multiplication by 6.0. Never treat 4.2 overs as 4.2 decimal overs. Rounding only the final mean prevents accumulated per-match rounding error. SUM/AVG normally ignore NULL, so explicit completeness checks prevent missing data from yielding a deceptively complete total or average.

No index or schema change was added. Existing bowling/player-match and identity indexes support access paths, but both aggregation levels have real work. At larger scale, benchmark representative player/venue history and assess whether a maintained per-match projection is justified. Do not add a runs-only index as a presumed fix for multi-row overs and aggregate thresholds.

## Verification and checkpoint

The full suite passes **291 tests**; lint, formatting and whitespace checks pass. Six focused tests cover three-match eligibility and arithmetic versus pooled economy; 23-ball exclusion and short extra matches; two innings totaling four overs without duplicate matches; separate/unknown venues; unknown balls/runs/wickets; and deleted rows/players plus super-over exclusions. All test mutations occur in isolated temporary databases.

Question 14 is complete. Question 15 has not been implemented. Say **NEXT** to proceed to Question 15.
