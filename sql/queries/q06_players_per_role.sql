-- Q06: Count active players for every defined playing role.
SELECT
    r.name AS playing_role,
    COUNT(p.player_id) AS player_count
FROM playing_roles AS r
LEFT JOIN v_active_players AS p ON p.role_id = r.role_id
GROUP BY r.role_id, r.name
ORDER BY player_count DESC, r.name ASC, r.role_id ASC;
