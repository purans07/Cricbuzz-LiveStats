-- Q05: Count confirmed completed wins in the selected stored dataset.
SELECT
    t.name AS team_name,
    COUNT(m.match_id) AS total_wins
FROM teams AS t
LEFT JOIN matches AS m
    ON m.winner_team_id = t.team_id
   AND m.status = 'completed'
   AND m.result_type = 'win'
GROUP BY t.team_id, t.name
ORDER BY total_wins DESC, t.name ASC, t.team_id ASC;
