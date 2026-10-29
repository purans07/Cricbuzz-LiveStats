-- Q12: Completed international-team wins by known venue/team country.
SELECT
    t.name AS team_name,
    SUM(CASE
        WHEN v.country_id = t.country_id THEN 1 ELSE 0
    END) AS home_wins,
    SUM(CASE
        WHEN v.country_id IS NOT NULL AND t.country_id IS NOT NULL
             AND v.country_id <> t.country_id THEN 1 ELSE 0
    END) AS away_wins,
    SUM(CASE
        WHEN m.match_id IS NOT NULL
             AND (v.country_id IS NULL OR t.country_id IS NULL)
        THEN 1 ELSE 0
    END) AS unclassified_wins
FROM teams AS t
LEFT JOIN matches AS m
    ON m.winner_team_id = t.team_id
   AND m.status = 'completed'
   AND m.result_type = 'win'
LEFT JOIN venues AS v ON v.venue_id = m.venue_id
WHERE t.is_international = 1
GROUP BY t.team_id, t.name
ORDER BY t.name ASC, t.team_id ASC;
