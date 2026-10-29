-- Q25: Completed batting matches in a caller-bound whole-quarter UTC window.
WITH match_scores AS (
    SELECT b.player_id,b.match_id,
           CAST(SUBSTR(m.starts_at,1,4) AS INTEGER)*4
             +(CAST(SUBSTR(m.starts_at,6,2) AS INTEGER)-1)/3 AS quarter_index,
           CASE WHEN COUNT(*)=COUNT(b.runs) THEN SUM(b.runs) END AS runs,
           CASE WHEN COUNT(*)=COUNT(b.balls_faced) THEN SUM(b.balls_faced) END AS balls
    FROM v_active_batting b JOIN matches m ON m.match_id=b.match_id
    WHERE m.status='completed'
      AND m.starts_at>=:window_start AND m.starts_at<:window_end
    GROUP BY b.player_id,b.match_id
), quarters AS (
    SELECT player_id,quarter_index,COUNT(*) AS batting_matches,
           CASE WHEN COUNT(runs)=COUNT(*) THEN AVG(1.0*runs) END AS average_runs,
           CASE WHEN COUNT(runs)=COUNT(*) AND COUNT(balls)=COUNT(*)
                     AND MIN(balls)>0
                THEN AVG(100.0*runs/balls) END AS average_strike_rate
    FROM match_scores GROUP BY player_id,quarter_index
), eligible AS (
    SELECT player_id,COUNT(*) AS observed_quarters,
           AVG(1.0*quarter_index) AS mean_quarter,
           CASE WHEN COUNT(average_runs)=COUNT(*)
                THEN AVG(average_runs) END AS mean_runs,
           CASE WHEN COUNT(average_strike_rate)=COUNT(*)
                THEN AVG(average_strike_rate) END AS mean_strike_rate
    FROM quarters GROUP BY player_id
    HAVING COUNT(*)>=6 AND MIN(batting_matches)>=3
), slopes AS (
    SELECT e.player_id,e.observed_quarters,
           SUM((q.quarter_index-e.mean_quarter)*(q.average_runs-e.mean_runs))
             /NULLIF(SUM((q.quarter_index-e.mean_quarter)*(q.quarter_index-e.mean_quarter)),0) AS runs_slope,
           SUM((q.quarter_index-e.mean_quarter)*(q.average_strike_rate-e.mean_strike_rate))
             /NULLIF(SUM((q.quarter_index-e.mean_quarter)*(q.quarter_index-e.mean_quarter)),0) AS strike_rate_slope
    FROM eligible e JOIN quarters q ON q.player_id=e.player_id
    GROUP BY e.player_id
), previous AS (
    SELECT q.*,LAG(q.quarter_index) OVER w AS previous_quarter_index,
           LAG(q.average_runs) OVER w AS previous_runs,
           LAG(q.average_strike_rate) OVER w AS previous_strike_rate
    FROM quarters q JOIN eligible e ON e.player_id=q.player_id
    WINDOW w AS (PARTITION BY q.player_id ORDER BY q.quarter_index)
), changes AS (
    SELECT *,CASE WHEN quarter_index=previous_quarter_index+1
                  THEN average_runs-previous_runs END AS runs_change,
           CASE WHEN quarter_index=previous_quarter_index+1
                THEN average_strike_rate-previous_strike_rate END AS strike_rate_change
    FROM previous
)
SELECT p.player_id,p.full_name AS player_name,
       CAST(c.quarter_index/4 AS INTEGER) AS year,c.quarter_index%4+1 AS quarter,
       c.batting_matches,s.observed_quarters,
       ROUND(c.average_runs,2) AS average_runs,
       ROUND(c.average_strike_rate,2) AS average_strike_rate,
       ROUND(c.runs_change,2) AS runs_change,
       ROUND(c.strike_rate_change,2) AS strike_rate_change,
       CASE WHEN c.runs_change IS NULL OR c.strike_rate_change IS NULL THEN NULL
            WHEN c.runs_change>=0 AND c.strike_rate_change>=0
                 AND (c.runs_change>5 OR c.strike_rate_change>5) THEN 'Improving'
            WHEN c.runs_change<=0 AND c.strike_rate_change<=0
                 AND (c.runs_change< -5 OR c.strike_rate_change< -5) THEN 'Declining'
            ELSE 'Stable' END AS quarterly_trend,
       CASE WHEN c.previous_quarter_index IS NULL THEN 'first_observed_quarter'
            WHEN c.quarter_index<>c.previous_quarter_index+1 THEN 'quarter_gap'
            WHEN c.runs_change IS NULL OR c.strike_rate_change IS NULL
                 THEN 'incomplete_metrics' ELSE 'compared' END AS comparison_status,
       ROUND(s.runs_slope,4) AS runs_slope_per_quarter,
       ROUND(s.strike_rate_slope,4) AS strike_rate_slope_per_quarter,
       CASE WHEN s.runs_slope IS NULL OR s.strike_rate_slope IS NULL THEN NULL
            WHEN s.runs_slope>=0 AND s.strike_rate_slope>=0
                 AND (s.runs_slope>1 OR s.strike_rate_slope>1) THEN 'Career Ascending'
            WHEN s.runs_slope<=0 AND s.strike_rate_slope<=0
                 AND (s.runs_slope< -1 OR s.strike_rate_slope< -1) THEN 'Career Declining'
            ELSE 'Career Stable' END AS career_phase
FROM changes c JOIN slopes s ON s.player_id=c.player_id
JOIN players p ON p.player_id=c.player_id
ORDER BY p.player_id,c.quarter_index;
