-- Q10: Up to twenty stored completed matches; known completion times first.
SELECT
    m.description AS match_description,
    t1.name AS team1_name,
    t2.name AS team2_name,
    winner.name AS winning_team,
    m.margin_value AS victory_margin,
    m.margin_unit AS victory_type,
    v.name AS venue_name
FROM matches AS m
JOIN match_teams AS mt1 ON mt1.match_id = m.match_id AND mt1.slot = 1
JOIN teams AS t1 ON t1.team_id = mt1.team_id
JOIN match_teams AS mt2 ON mt2.match_id = m.match_id AND mt2.slot = 2
JOIN teams AS t2 ON t2.team_id = mt2.team_id
LEFT JOIN teams AS winner ON winner.team_id = m.winner_team_id
LEFT JOIN venues AS v ON v.venue_id = m.venue_id
WHERE m.status = 'completed'
ORDER BY (m.completed_at IS NULL) ASC,
         m.completed_at DESC, m.starts_at DESC, m.match_id DESC
LIMIT 20;
