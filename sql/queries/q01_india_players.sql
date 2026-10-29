-- Q01: Players representing India on the bound analysis date.
-- The as_of_date parameter uses YYYY-MM-DD; membership end dates are inclusive.
SELECT
    p.full_name,
    r.name AS playing_role,
    p.batting_style,
    p.bowling_style
FROM v_active_players AS p
LEFT JOIN playing_roles AS r ON r.role_id = p.role_id
WHERE EXISTS (
    SELECT 1
    FROM player_team_memberships AS pm
    JOIN teams AS t ON t.team_id = pm.team_id
    JOIN countries AS c ON c.country_id = t.country_id
    WHERE pm.player_id = p.player_id
      AND t.is_international = 1
      AND c.name = 'India'
      AND pm.valid_from <= :as_of_date
      AND (pm.valid_to IS NULL OR pm.valid_to >= :as_of_date)
)
ORDER BY p.full_name, p.player_id;
