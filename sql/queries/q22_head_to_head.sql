WITH pair_matches AS (
    SELECT m.*, MIN(a.team_id,b.team_id) AS team_a_id,
           MAX(a.team_id,b.team_id) AS team_b_id,
           i.batting_team_id AS first_batting_team_id
    FROM matches m
    JOIN match_teams a ON a.match_id=m.match_id AND a.slot=1
    JOIN match_teams b ON b.match_id=m.match_id AND b.slot=2
    LEFT JOIN innings i ON i.match_id=m.match_id
        AND i.innings_number=1 AND i.is_super_over=0
    WHERE m.status='completed'
      AND m.starts_at >= :window_start AND m.starts_at < :window_end
), eligible AS (
    SELECT team_a_id,team_b_id FROM pair_matches
    GROUP BY team_a_id,team_b_id HAVING COUNT(*) >= 5
), scoped AS (
    SELECT p.* FROM pair_matches p
    JOIN eligible e USING (team_a_id,team_b_id)
), team_results AS (
    SELECT s.*,team_a_id AS team_id FROM scoped s
    UNION ALL
    SELECT s.*,team_b_id AS team_id FROM scoped s
)
SELECT r.team_a_id,r.team_b_id,a.name AS team_a,b.name AS team_b,
       r.team_id,t.name AS team_name,COUNT(*) AS matches_played,
       SUM(CASE WHEN r.winner_team_id=r.team_id THEN 1 ELSE 0 END) AS wins,
       SUM(r.result_type='pending') AS unknown_results,
       CASE WHEN SUM(r.result_type='pending')=0
            THEN ROUND(100.0*SUM(CASE WHEN r.winner_team_id=r.team_id THEN 1 ELSE 0 END)/COUNT(*),2)
       END AS win_percentage,
       SUM(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='runs' THEN 1 ELSE 0 END) AS run_margin_wins,
       ROUND(AVG(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='runs' THEN r.margin_value END),2) AS average_win_margin_runs,
       SUM(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='wickets' THEN 1 ELSE 0 END) AS wicket_margin_wins,
       ROUND(AVG(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit='wickets' THEN r.margin_value END),2) AS average_win_margin_wickets,
       SUM(CASE WHEN r.winner_team_id=r.team_id AND r.margin_unit IS NULL THEN 1 ELSE 0 END) AS wins_missing_margin
FROM team_results r
JOIN teams a ON a.team_id=r.team_a_id
JOIN teams b ON b.team_id=r.team_b_id
JOIN teams t ON t.team_id=r.team_id
GROUP BY r.team_a_id,r.team_b_id,r.team_id
ORDER BY r.team_a_id,r.team_b_id,r.team_id;
