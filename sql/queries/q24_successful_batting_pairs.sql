-- Q24: Adjacent-position combined-score proxy, not observed stand runs.
WITH appearances AS (
    SELECT MIN(a.player_id,b.player_id) AS player_a_id,
           MAX(a.player_id,b.player_id) AS player_b_id,
           a.innings_id,a.runs+b.runs AS combined_runs
    FROM v_active_batting a
    JOIN v_active_batting b ON b.innings_id=a.innings_id
        AND b.batting_position=a.batting_position+1
), summaries AS (
    SELECT player_a_id,player_b_id,COUNT(*) AS pair_appearances,
           COUNT(combined_runs) AS known_scores,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN AVG(1.0*combined_runs) END AS average_combined_runs,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN SUM(combined_runs>50) END AS scores_above_50,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN MAX(combined_runs) END AS highest_combined_runs,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN 100.0*SUM(combined_runs>50)/COUNT(*) END AS success_percentage
    FROM appearances GROUP BY player_a_id,player_b_id
    HAVING COUNT(*)>=5
), ranked AS (
    SELECT player_a_id,player_b_id,DENSE_RANK() OVER (
        ORDER BY success_percentage DESC,average_combined_runs DESC,
                 highest_combined_runs DESC
    ) AS success_rank
    FROM summaries WHERE known_scores=pair_appearances
)
SELECT r.success_rank,s.player_a_id,a.full_name AS player_a_name,
       s.player_b_id,b.full_name AS player_b_name,s.pair_appearances,
       s.known_scores,s.pair_appearances-s.known_scores AS missing_scores,
       ROUND(s.average_combined_runs,2) AS average_combined_runs,
       s.scores_above_50,s.highest_combined_runs,
       ROUND(s.success_percentage,2) AS success_percentage,
       CASE WHEN s.known_scores=s.pair_appearances THEN 'ranked'
            ELSE 'incomplete_scores' END AS coverage_status
FROM summaries s
JOIN players a ON a.player_id=s.player_a_id
JOIN players b ON b.player_id=s.player_b_id
LEFT JOIN ranked r ON r.player_a_id=s.player_a_id AND r.player_b_id=s.player_b_id
ORDER BY r.success_rank IS NULL,r.success_rank,s.player_a_id,s.player_b_id;
