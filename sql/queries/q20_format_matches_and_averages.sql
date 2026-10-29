-- Q20: Latest selected-source international format careers, >=20 known matches.
WITH format_careers AS (
    SELECT p.player_id, p.full_name,
        CASE WHEN f.code = 'TEST' THEN 'Test'
             WHEN f.code = 'ODI' THEN 'ODI'
             ELSE 'T20' END AS format_group,
        c.matches_played,
        CASE WHEN c.dismissals > 0 THEN 1.0 * c.runs / c.dismissals
             WHEN c.dismissals IS NULL THEN c.reported_batting_average
        END AS batting_average
    FROM v_latest_career AS c
    JOIN players AS p ON p.player_id = c.player_id
    JOIN formats AS f ON f.format_id = c.format_id
    JOIN sources AS s ON s.source_id = c.source_id
    WHERE s.name = :source_name
      AND c.scope = 'career'
      AND f.level = 'international'
      AND f.code IN ('TEST', 'ODI', 'T20', 'T20I', 'INTERNATIONAL_T20')
)
SELECT
    full_name AS player_name,
    MAX(CASE WHEN format_group = 'Test' THEN matches_played END) AS test_matches,
    ROUND(MAX(CASE WHEN format_group = 'Test' THEN batting_average END), 2)
        AS test_batting_average,
    MAX(CASE WHEN format_group = 'ODI' THEN matches_played END) AS odi_matches,
    ROUND(MAX(CASE WHEN format_group = 'ODI' THEN batting_average END), 2)
        AS odi_batting_average,
    MAX(CASE WHEN format_group = 'T20' THEN matches_played END) AS t20_matches,
    ROUND(MAX(CASE WHEN format_group = 'T20' THEN batting_average END), 2)
        AS t20_batting_average,
    SUM(matches_played) AS total_known_matches
FROM format_careers
GROUP BY player_id, full_name
HAVING COUNT(*) = COUNT(DISTINCT format_group)
   AND COUNT(*) = COUNT(matches_played)
   AND SUM(matches_played) >= 20
ORDER BY full_name ASC, player_id ASC;
