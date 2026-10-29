-- Q11: Compare players with evidenced appearances in at least two target formats.
WITH eligible_careers AS (
    SELECT p.player_id, p.full_name, f.code, c.runs, c.dismissals
    FROM v_latest_career AS c
    JOIN players AS p ON p.player_id = c.player_id
    JOIN formats AS f ON f.format_id = c.format_id
    JOIN sources AS s ON s.source_id = c.source_id
    WHERE s.name = :source_name
      AND c.scope = 'career'
      AND f.code IN ('TEST', 'ODI', 'T20I')
      AND f.level = 'international'
      AND c.matches_played > 0
)
SELECT
    player_id,
    full_name AS player_name,
    MAX(CASE WHEN code = 'TEST' THEN runs END) AS test_runs,
    MAX(CASE WHEN code = 'ODI' THEN runs END) AS odi_runs,
    MAX(CASE WHEN code = 'T20I' THEN runs END) AS t20i_runs,
    CASE
        WHEN COUNT(*) = COUNT(runs) AND COUNT(*) = COUNT(dismissals)
        THEN ROUND(1.0 * SUM(runs) / NULLIF(SUM(dismissals), 0), 2)
        ELSE NULL
    END AS overall_batting_average
FROM eligible_careers
GROUP BY player_id, full_name
HAVING COUNT(DISTINCT code) >= 2
ORDER BY full_name ASC, player_id ASC;
