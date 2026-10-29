-- Q23: Match-based recent batting form across all formats; explicit UTC cutoff.
WITH match_scores AS (
    SELECT b.player_id,b.match_id,m.starts_at,
           CASE WHEN COUNT(*)=COUNT(b.runs) THEN SUM(b.runs) END AS runs,
           CASE WHEN COUNT(*)=COUNT(b.balls_faced) THEN SUM(b.balls_faced) END AS balls
    FROM v_active_batting b
    JOIN matches m ON m.match_id=b.match_id
    WHERE m.status='completed' AND m.starts_at < :as_of_utc
    GROUP BY b.player_id,b.match_id,m.starts_at
), ordered AS (
    SELECT *,ROW_NUMBER() OVER (
        PARTITION BY player_id ORDER BY starts_at DESC,match_id DESC
    ) AS recency
    FROM match_scores
), recent AS (
    SELECT * FROM ordered WHERE recency<=10
), metrics AS (
    SELECT player_id,COUNT(*) AS matches_last_10,
           SUM(recency<=5) AS matches_last_5,
           CASE WHEN COUNT(runs)=COUNT(*) THEN AVG(runs) END AS average_runs_last_10,
           CASE WHEN COUNT(CASE WHEN recency<=5 THEN runs END)=SUM(recency<=5)
                THEN AVG(CASE WHEN recency<=5 THEN runs END) END AS average_runs_last_5,
           CASE WHEN COUNT(runs)=COUNT(*) AND COUNT(balls)=COUNT(*)
                THEN 100.0*SUM(runs)/NULLIF(SUM(balls),0) END AS strike_rate_last_10,
           CASE WHEN COUNT(CASE WHEN recency<=5 THEN runs END)=SUM(recency<=5)
                     AND COUNT(CASE WHEN recency<=5 THEN balls END)=SUM(recency<=5)
                THEN 100.0*SUM(CASE WHEN recency<=5 THEN runs END)
                     /NULLIF(SUM(CASE WHEN recency<=5 THEN balls END),0) END AS strike_rate_last_5,
           CASE WHEN COUNT(runs)=COUNT(*) THEN SUM(runs>50) END AS scores_above_50_last_10,
           CASE WHEN COUNT(CASE WHEN recency<=5 THEN runs END)=SUM(recency<=5)
                THEN SUM(CASE WHEN recency<=5 AND runs>50 THEN 1 ELSE 0 END) END AS scores_above_50_last_5
    FROM recent GROUP BY player_id
), dispersion AS (
    SELECT m.*,SQRT(AVG((r.runs-m.average_runs_last_10)
                       *(r.runs-m.average_runs_last_10))) AS standard_deviation_runs
    FROM metrics m JOIN recent r ON r.player_id=m.player_id
    GROUP BY m.player_id
), indicators AS (
    SELECT *,average_runs_last_5-average_runs_last_10 AS runs_momentum,
           strike_rate_last_5-strike_rate_last_10 AS strike_rate_change,
           100.0/(1.0+standard_deviation_runs/25.0) AS consistency_score
    FROM dispersion
)
SELECT p.player_id,p.full_name AS player_name,i.matches_last_5,i.matches_last_10,
       ROUND(i.average_runs_last_5,2) AS average_runs_last_5,
       ROUND(i.average_runs_last_10,2) AS average_runs_last_10,
       ROUND(i.runs_momentum,2) AS runs_momentum,
       ROUND(i.strike_rate_last_5,2) AS strike_rate_last_5,
       ROUND(i.strike_rate_last_10,2) AS strike_rate_last_10,
       ROUND(i.strike_rate_change,2) AS strike_rate_change,
       i.scores_above_50_last_5,i.scores_above_50_last_10,
       ROUND(i.standard_deviation_runs,2) AS standard_deviation_runs,
       ROUND(i.consistency_score,2) AS consistency_score,
       CASE WHEN i.matches_last_10<10 OR i.average_runs_last_10 IS NULL
                      OR i.strike_rate_change IS NULL THEN NULL
            WHEN i.average_runs_last_5>=50 AND i.runs_momentum>=0
                 AND i.strike_rate_change>=0 AND i.consistency_score>=50
                 AND i.scores_above_50_last_5>=2 THEN 'Excellent Form'
            WHEN i.average_runs_last_5>=35 AND i.runs_momentum>=-5
                 AND i.strike_rate_change>=-10 AND i.consistency_score>=40
                 AND i.scores_above_50_last_5>=1 THEN 'Good Form'
            WHEN i.average_runs_last_5>=20 AND i.consistency_score>=25 THEN 'Average Form'
            ELSE 'Poor Form' END AS form_category,
       CASE WHEN i.matches_last_10<10 THEN 'insufficient_history'
            WHEN i.average_runs_last_10 IS NULL OR i.strike_rate_change IS NULL
                 THEN 'incomplete_metrics' ELSE 'classified' END AS coverage_status
FROM indicators i JOIN players p ON p.player_id=i.player_id
ORDER BY p.player_id;
