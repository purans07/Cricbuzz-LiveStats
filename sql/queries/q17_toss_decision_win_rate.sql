-- Q17: Toss-winner win percentage over completed, resolved-result matches.
WITH toss_options (toss_decision) AS (
    VALUES ('bat'), ('bowl')
)
SELECT
    d.toss_decision,
    COUNT(m.match_id) AS eligible_matches,
    SUM(CASE WHEN m.winner_team_id = m.toss_winner_id
             THEN 1 ELSE 0 END) AS toss_winner_match_wins,
    ROUND(
        100.0 * SUM(CASE WHEN m.winner_team_id = m.toss_winner_id
                         THEN 1 ELSE 0 END)
        / NULLIF(COUNT(m.match_id), 0), 2
    ) AS win_percentage
FROM toss_options AS d
LEFT JOIN matches AS m
    ON m.toss_decision = d.toss_decision
   AND m.status = 'completed'
   AND m.result_type IN ('win', 'draw', 'tie', 'no_result')
   AND m.toss_winner_id IS NOT NULL
GROUP BY d.toss_decision
ORDER BY d.toss_decision ASC;
