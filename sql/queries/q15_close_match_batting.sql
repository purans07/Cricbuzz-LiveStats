-- Q15: Batting contribution per completed close match, then per player.
WITH close_player_matches AS (
    SELECT
        b.player_id, b.match_id, b.team_id, m.winner_team_id,
        CASE WHEN COUNT(*) = COUNT(b.runs)
             THEN SUM(b.runs)
        END AS match_runs
    FROM v_active_batting AS b
    JOIN matches AS m ON m.match_id = b.match_id
    WHERE m.status = 'completed'
      AND m.result_type = 'win'
      AND (
          (m.margin_unit = 'runs' AND m.margin_value < 50)
          OR (m.margin_unit = 'wickets' AND m.margin_value < 5)
      )
    GROUP BY b.player_id, b.match_id, b.team_id, m.winner_team_id
)
SELECT
    p.full_name AS player_name,
    CASE WHEN COUNT(*) = COUNT(q.match_runs)
         THEN ROUND(AVG(q.match_runs), 2)
    END AS average_runs,
    COUNT(*) AS total_close_matches_played,
    SUM(CASE WHEN q.team_id = q.winner_team_id THEN 1 ELSE 0 END)
        AS team_wins_when_batted
FROM close_player_matches AS q
JOIN players AS p ON p.player_id = q.player_id
GROUP BY p.player_id, p.full_name
ORDER BY (average_runs IS NULL) ASC, average_runs DESC,
         total_close_matches_played DESC, p.player_id ASC;
