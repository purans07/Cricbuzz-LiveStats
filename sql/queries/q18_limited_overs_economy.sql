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
