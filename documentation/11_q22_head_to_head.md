# Phase 11 — Question 22: head-to-head analysis

## Assignment and interpretation before SQL

For each pair with at least five matches in the last three years, calculate total matches, each team's wins, average victory margins, batting-first versus bowling-first performance at different venues, and each team's overall win percentage.

This is descriptive history to support analysis, not a trained prediction or a probability of winning the next match. All stored formats are combined because no format restriction is specified. Differences in format, opposition strength and venue coverage can affect comparisons.

Use completed matches only, including completed matches whose structured result remains pending. This excludes unfinished and abandoned fixtures. Each pair qualifies on at least five completed matches across all venues, not five per venue. Dates use scheduled starts in the half-open interval [window_start, window_end); unknown dates are excluded. A match starting before the window is excluded even if it finishes inside it. Bind a three-calendar-year interval outside SQL; for a February 29 endpoint clamp the earlier anniversary to February 28. Do not substitute 1,095 days. Sample bounds are 2023-10-01 through 2026-10-01 UTC; live bounds are 2023-10-22 07:52:06 through the saved capture timestamp 2026-10-22 07:52:06 UTC. These are reproducible snapshots, not a current-data claim.

Wins require the structured winner. Draws, ties and no results remain in the denominator as resolved non-wins. Pending results are counted separately and suppress the whole group's win percentage; they never silently become losses. Confirmed wins remain reportable. A percentage is 100 × wins / completed matches only when every outcome in that group is resolved.

Average run and wicket victory margins separately, over wins with that known unit. Show contributing win counts and wins missing margins; a missing margin does not become zero. No wins in a unit means NULL, not a zero average. These are averages of available margins, not an assertion of complete coverage.

Actual ordinary innings number 1 determines batting first. Ignore super overs and do not infer order from toss decisions or a later imported innings. Missing first innings becomes an explicit unknown condition. For multi-innings Tests, the initial batting order defines the condition. Missing venues retain a NULL venue group.

## Concepts, relationships and execution plan before SQL

Use joins, common table expressions (CTEs), canonical ID pairs, HAVING, UNION ALL, conditional aggregation, CASE and NULL-aware averages. The two queries share the same qualifying-match pipeline. The summary has one row per pair/team, making both teams' figures explicit. The second has one row per pair/team/venue/condition. Summary counts are repeated for the two teams by design; do not sum them as distinct matches or add summary counts to venue counts.

`matches` stores dates, result and typed margin; `match_teams` supplies exactly one participant in each slot; `teams` supplies labels; `innings` identifies first batting order; `venues` supplies optional labels. Pair identity uses the smaller/larger team IDs, never names or slot order. Same-named venues remain distinct by ID. No batting/bowling performance joins are needed.

Filter completed dated fixtures, canonicalize pairs, retain pairs with five matches, expand each match to its two team perspectives, then aggregate. The unique match/innings-number constraint prevents first-innings duplication. Avoid joining every innings, which would multiply Test match counts. Team and venue IDs determine grouping; names are display labels.

## Queries and line-by-line explanation

### q22_head_to_head.sql

```sql
WITH pair_matches AS (
    SELECT m.*, MIN(a.team_id,b.team_id) AS team_a_id,
           MAX(a.team_id,b.team_id) AS team_b_id,
           i.batting_team_id AS first_batting_team_id
    FROM matches m
    JOIN match_teams a ON a.match_id=m.match_id AND a.slot=1
    JOIN match_teams b ON b.match_id=m.match_id AND b.slot=2
    LEFT JOIN innings i ON i.match_id=m.match_id
        AND i.innings_number=1 AND i.is_super_over=0
    WHERE m.status='completed'
      AND m.starts_at >= :window_start AND m.starts_at < :window_end
), eligible AS (
    SELECT team_a_id,team_b_id FROM pair_matches
    GROUP BY team_a_id,team_b_id HAVING COUNT(*) >= 5
), scoped AS (
    SELECT p.* FROM pair_matches p
    JOIN eligible e USING (team_a_id,team_b_id)
), team_results AS (
    SELECT s.*,team_a_id AS team_id FROM scoped s
    UNION ALL
    SELECT s.*,team_b_id AS team_id FROM scoped s
)
SELECT r.team_a_id,r.team_b_id,a.name AS team_a,b.name AS team_b,
       r.team_id,t.name AS team_name,COUNT(*) AS matches_played,
       SUM(CASE WHEN r.winner_team_id=r.team_id THEN 1 ELSE 0 END) AS wins,
       SUM(r.result_type='pending') AS unknown_results,
       CASE WHEN SUM(r.result_type='pending')=0
            THEN ROUND(100.0*SUM(CASE WHEN r.winner_team_id=r.team_id THEN 1 ELSE 0 END)/COUNT(*),2)
       END AS win_percentage,
       SUM(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='runs' THEN 1 ELSE 0 END) AS run_margin_wins,
       ROUND(AVG(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='runs' THEN r.margin_value END),2) AS average_win_margin_runs,
       SUM(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='wickets' THEN 1 ELSE 0 END) AS wicket_margin_wins,
       ROUND(AVG(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='wickets' THEN r.margin_value END),2) AS average_win_margin_wickets,
       SUM(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit IS NULL THEN 1 ELSE 0 END) AS wins_missing_margin
FROM team_results r
JOIN teams a ON a.team_id=r.team_a_id
JOIN teams b ON b.team_id=r.team_b_id
JOIN teams t ON t.team_id=r.team_id
GROUP BY r.team_a_id,r.team_b_id,r.team_id
ORDER BY r.team_a_id,r.team_b_id,r.team_id;
```

| Line | Explanation |
| --- | --- |
| 1 | Begin the per-match CTE. |
| 2 | Keep match fields and derive the smaller participant ID. |
| 3 | Derive the larger participant ID, completing a stable pair. |
| 4 | Carry actual first batting team, if available. |
| 5 | Read fixtures. |
| 6 | Find the participant in slot 1. |
| 7 | Find the participant in slot 2. |
| 8 | Optionally join the first innings for this match. |
| 9 | Require ordinary innings number 1, excluding super overs. |
| 10 | Keep completed fixtures. |
| 11 | Apply inclusive lower and exclusive upper UTC bounds. |
| 12 | Begin eligible-pair aggregation. |
| 13 | Select pair identities. |
| 14 | Require five matches across the entire window. |
| 15 | Begin the qualifying fixture set. |
| 16 | Keep each qualifying fixture. |
| 17 | Match the two canonical pair IDs. |
| 18 | Begin two team perspectives per match. |
| 19 | Assign the first canonical team perspective. |
| 20 | Append without eliminating legitimate fixture rows. |
| 21 | Assign the second canonical team perspective. |
| 22 | End the shared pipeline. |
| 23 | Select pair IDs and names. |
| 24 | Select perspective ID/name and count completed matches. |
| 25 | Count only confirmed wins for this perspective. |
| 26 | Audit unknown structured outcomes. |
| 27 | Permit a percentage only when outcomes are complete. |
| 28 | Divide confirmed wins by all completed matches using real arithmetic. |
| 29 | Finish the conditional percentage. |
| 30 | Count wins with a known run margin. |
| 31 | Average run margins only over those wins. |
| 32 | Count wins with a known wicket margin. |
| 33 | Average wicket margins only over those wins. |
| 34 | Count confirmed wins whose margin is unavailable. |
| 35 | Read the two-perspective fixture set. |
| 36 | Attach canonical first team label. |
| 37 | Attach canonical second team label. |
| 38 | Attach perspective team label. |
| 39 | Aggregate at pair/team grain. |
| 40 | Use stable pair/team display order. |

### q22_head_to_head_venues.sql

```sql
WITH pair_matches AS (
    SELECT m.*, MIN(a.team_id,b.team_id) AS team_a_id,
           MAX(a.team_id,b.team_id) AS team_b_id,
           i.batting_team_id AS first_batting_team_id
    FROM matches m
    JOIN match_teams a ON a.match_id=m.match_id AND a.slot=1
    JOIN match_teams b ON b.match_id=m.match_id AND b.slot=2
    LEFT JOIN innings i ON i.match_id=m.match_id
        AND i.innings_number=1 AND i.is_super_over=0
    WHERE m.status='completed'
      AND m.starts_at >= :window_start AND m.starts_at < :window_end
), eligible AS (
    SELECT team_a_id,team_b_id FROM pair_matches
    GROUP BY team_a_id,team_b_id HAVING COUNT(*) >= 5
), scoped AS (
    SELECT p.* FROM pair_matches p
    JOIN eligible e USING (team_a_id,team_b_id)
), team_results AS (
    SELECT s.*,team_a_id AS team_id FROM scoped s
    UNION ALL
    SELECT s.*,team_b_id AS team_id FROM scoped s
)
SELECT r.team_a_id,r.team_b_id,r.team_id,t.name AS team_name,
       r.venue_id,v.name AS venue_name,
       CASE WHEN r.first_batting_team_id IS NULL THEN 'unknown'
            WHEN r.first_batting_team_id=r.team_id THEN 'batting_first'
            ELSE 'bowling_first' END AS innings_condition,
       COUNT(*) AS matches_played,
       SUM(CASE WHEN r.winner_team_id=r.team_id THEN 1 ELSE 0 END) AS wins,
       SUM(r.result_type='pending') AS unknown_results,
       CASE WHEN SUM(r.result_type='pending')=0
            THEN ROUND(100.0*SUM(CASE WHEN r.winner_team_id=r.team_id THEN 1 ELSE 0 END)/COUNT(*),2)
       END AS win_percentage
FROM team_results r
JOIN teams t ON t.team_id=r.team_id
LEFT JOIN venues v ON v.venue_id=r.venue_id
GROUP BY r.team_a_id,r.team_b_id,r.team_id,r.venue_id,innings_condition
ORDER BY r.team_a_id,r.team_b_id,r.team_id,r.venue_id,innings_condition;
```

| Line | Explanation |
| --- | --- |
| 1 | Begin the per-match CTE. |
| 2 | Keep match fields and derive the smaller participant ID. |
| 3 | Derive the larger participant ID, completing a stable pair. |
| 4 | Carry actual first batting team, if available. |
| 5 | Read fixtures. |
| 6 | Find the participant in slot 1. |
| 7 | Find the participant in slot 2. |
| 8 | Optionally join the first innings for this match. |
| 9 | Require ordinary innings number 1, excluding super overs. |
| 10 | Keep completed fixtures. |
| 11 | Apply inclusive lower and exclusive upper UTC bounds. |
| 12 | Begin eligible-pair aggregation. |
| 13 | Select pair identities. |
| 14 | Require five matches across the entire window. |
| 15 | Begin the qualifying fixture set. |
| 16 | Keep each qualifying fixture. |
| 17 | Match the two canonical pair IDs. |
| 18 | Begin two team perspectives per match. |
| 19 | Assign the first canonical team perspective. |
| 20 | Append without eliminating legitimate fixture rows. |
| 21 | Assign the second canonical team perspective. |
| 22 | End the shared pipeline. |
| 23 | Select pair and perspective identity. |
| 24 | Keep venue identity and optional label. |
| 25 | Label unavailable first innings as unknown. |
| 26 | Label the first batting team perspective. |
| 27 | Label the opposing perspective as bowling first. |
| 28 | Count fixtures in this venue/condition group. |
| 29 | Count confirmed perspective wins. |
| 30 | Audit unknown outcomes in the group. |
| 31 | Require complete group outcomes for a percentage. |
| 32 | Calculate wins per completed fixture as a percentage. |
| 33 | Finish the conditional percentage. |
| 34 | Read eligible team perspectives. |
| 35 | Attach the perspective label. |
| 36 | Retain missing venue metadata with a left join. |
| 37 | Group by IDs and actual innings condition. |
| 38 | Order groups deterministically. |

## Running and verified results

Execute either SQL file with bound `window_start` and `window_end` strings on an existing read-only database connection. Both parameters must be normalized UTC timestamps and the caller must supply a valid three-calendar-year window. The SQL deliberately does not read the machine clock. The venue query applies pair eligibility before venue grouping.

Sample: 72 completed matches, one qualifying pair, two summary rows and eight venue/condition rows. Sample India XI: 37 wins, 51.39%, mean winning run margin 149.59 (37 wins). Sample Australia XI: 35 wins, 48.61%, mean winning run margin 137.31 (35 wins). Both wicket averages are NULL because there are no wicket-margin wins. These are fictional fixtures.

Live snapshot: no qualifying pairs in either output. Four stored fixtures cannot establish a five-match history; structured results and historical coverage are also limited. Empty output is not evidence that these teams have never met.

Full rows, bound timestamps and actual query plans are saved in [the execution report](11_q22_result.json). Queries were run read-only; no live API calls or working database mutations were needed.

## Measured plan and optimization

### sample summary

```text
CO-ROUTINE team_results
COMPOUND QUERY
LEFT-MOST SUBQUERY
MATERIALIZE eligible
SEARCH m USING INDEX idx_matches_status_date (status=?)
SEARCH a USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH b USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH i USING INDEX sqlite_autoindex_innings_1 (match_id=? AND innings_number=?) LEFT-JOIN
USE TEMP B-TREE FOR GROUP BY
SEARCH m USING INDEX idx_matches_status_date (status=?)
SEARCH a USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH b USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH i USING INDEX sqlite_autoindex_innings_1 (match_id=? AND innings_number=?) LEFT-JOIN
BLOOM FILTER ON e (team_a_id=? AND team_b_id=?)
SEARCH e USING AUTOMATIC COVERING INDEX (team_a_id=? AND team_b_id=?)
UNION ALL
SEARCH m USING INDEX idx_matches_status_date (status=?)
SEARCH a USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH b USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
BLOOM FILTER ON e (team_a_id=? AND team_b_id=?)
SEARCH e USING AUTOMATIC COVERING INDEX (team_a_id=? AND team_b_id=?)
SEARCH i USING INDEX sqlite_autoindex_innings_1 (match_id=? AND innings_number=?) LEFT-JOIN
SCAN r
SEARCH a USING INTEGER PRIMARY KEY (rowid=?)
SEARCH b USING INTEGER PRIMARY KEY (rowid=?)
SEARCH t USING INTEGER PRIMARY KEY (rowid=?)
USE TEMP B-TREE FOR GROUP BY
```

### sample venues

```text
CO-ROUTINE team_results
COMPOUND QUERY
LEFT-MOST SUBQUERY
MATERIALIZE eligible
SEARCH m USING INDEX idx_matches_status_date (status=?)
SEARCH a USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH b USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH i USING INDEX sqlite_autoindex_innings_1 (match_id=? AND innings_number=?) LEFT-JOIN
USE TEMP B-TREE FOR GROUP BY
SEARCH m USING INDEX idx_matches_status_date (status=?)
SEARCH a USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH b USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH i USING INDEX sqlite_autoindex_innings_1 (match_id=? AND innings_number=?) LEFT-JOIN
BLOOM FILTER ON e (team_a_id=? AND team_b_id=?)
SEARCH e USING AUTOMATIC COVERING INDEX (team_a_id=? AND team_b_id=?)
UNION ALL
SEARCH m USING INDEX idx_matches_status_date (status=?)
SEARCH a USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
SEARCH b USING INDEX sqlite_autoindex_match_teams_2 (match_id=? AND slot=?)
BLOOM FILTER ON e (team_a_id=? AND team_b_id=?)
SEARCH e USING AUTOMATIC COVERING INDEX (team_a_id=? AND team_b_id=?)
SEARCH i USING INDEX sqlite_autoindex_innings_1 (match_id=? AND innings_number=?) LEFT-JOIN
SCAN r
SEARCH t USING INTEGER PRIMARY KEY (rowid=?)
SEARCH v USING INTEGER PRIMARY KEY (rowid=?) LEFT-JOIN
USE TEMP B-TREE FOR GROUP BY
```

Existing status/date and participant/innings uniqueness indexes support fixture selection and keyed joins. SQLite materializes reused CTEs and uses temporary grouping/order structures as shown above. Both outputs share definitions but execute separately; a future dashboard could reuse an explicitly scoped intermediate result when history becomes large. No additional index is justified by this small fixture set. Never optimize by joining all innings or averaging mixed margin units.

## Validation and limits

Six focused tests cover match grain, five-match threshold across venues, start/end boundaries, separate units and missing margins, unresolved versus drawn outcomes, actual innings order independent of toss, and missing venue/first innings. The full suite passes 346 tests; lint, formatting and whitespace checks pass. Tests operate on temporary copies.

This report combines formats and treats every completed fixture equally. It does not estimate uncertainty, adjust for changing squads, validate a predictive model or repair missing historical coverage. Missing first-innings data is visible, not guessed. Unknown outcome groups withhold percentages.

Question 22 is complete. Question 23 awaits NEXT; Phase 11 remains in progress.
