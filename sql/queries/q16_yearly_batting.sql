-- Q16: Yearly match-based batting averages since 2020 (SQLite UTC years).
WITH match_batting AS (
    SELECT b.player_id, b.match_id,
        CASE WHEN COUNT(*) = COUNT(b.runs)
             THEN SUM(b.runs) END AS match_runs,
        CASE WHEN COUNT(*) = COUNT(b.balls_faced)
             THEN SUM(b.balls_faced) END AS match_balls
    FROM v_active_batting AS b
    GROUP BY b.player_id, b.match_id
), yearly_appearances AS (
    SELECT mp.player_id, m.match_id,
        CAST(SUBSTR(m.starts_at, 1, 4) AS INTEGER) AS match_year,
        mb.match_runs, mb.match_balls
    FROM v_active_match_players AS mp
    JOIN matches AS m ON m.match_id = mp.match_id
    LEFT JOIN match_batting AS mb
        ON mb.player_id = mp.player_id AND mb.match_id = mp.match_id
    WHERE m.starts_at >= '2020-01-01T00:00:00Z'
      AND m.status IN ('completed', 'live', 'abandoned')
      AND (m.status = 'completed' OR EXISTS (
          SELECT 1 FROM innings AS i
          WHERE i.match_id = m.match_id AND i.legal_balls > 0
      ))
      AND (mp.participation IN ('confirmed_xi', 'observed')
           OR mb.player_id IS NOT NULL)
)
SELECT p.full_name AS player_name, y.match_year,
    COUNT(*) AS matches_played,
    CASE WHEN COUNT(*) = COUNT(y.match_runs)
         THEN ROUND(AVG(y.match_runs), 2)
    END AS average_runs_per_match,
    CASE WHEN COUNT(*) = COUNT(y.match_runs)
              AND COUNT(*) = COUNT(y.match_balls)
         THEN ROUND(AVG(100.0 * y.match_runs / NULLIF(y.match_balls, 0)), 2)
    END AS average_strike_rate
FROM yearly_appearances AS y
JOIN players AS p ON p.player_id = y.player_id
GROUP BY p.player_id, p.full_name, y.match_year
HAVING COUNT(*) >= 5
ORDER BY p.full_name ASC, p.player_id ASC, y.match_year ASC;
