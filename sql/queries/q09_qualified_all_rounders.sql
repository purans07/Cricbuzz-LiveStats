-- Q09: All-rounders exceeding both career thresholds within the same format.
-- Bind source_name; each output row represents one player and format.
SELECT
    p.full_name AS player_name,
    c.runs AS total_runs,
    c.wickets AS total_wickets,
    f.code AS cricket_format
FROM v_latest_career AS c
JOIN players AS p ON p.player_id = c.player_id
JOIN playing_roles AS r ON r.role_id = p.role_id
JOIN formats AS f ON f.format_id = c.format_id
JOIN sources AS s ON s.source_id = c.source_id
WHERE r.name = 'All-rounder'
  AND s.name = :source_name
  AND c.scope = 'career'
  AND c.runs > 1000
  AND c.wickets > 50
ORDER BY c.runs DESC, c.wickets DESC, p.player_id ASC, f.code ASC;
