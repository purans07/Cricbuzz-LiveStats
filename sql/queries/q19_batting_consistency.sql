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
