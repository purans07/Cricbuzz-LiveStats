-- Q21: Complete-case weighted career score, ranked within each source format.
WITH career_metrics AS (
    SELECT c.player_id, c.format_id, f.code AS cricket_format,
        c.runs, c.wickets, c.catches, c.stumpings,
        CASE WHEN c.dismissals > 0 THEN 1.0 * c.runs / c.dismissals
             WHEN c.dismissals IS NULL THEN c.reported_batting_average
        END AS batting_average,
        CASE WHEN c.balls_faced > 0 THEN 100.0 * c.runs / c.balls_faced
             WHEN c.balls_faced IS NULL THEN c.reported_strike_rate
        END AS strike_rate,
        CASE WHEN c.wickets > 0 THEN 1.0 * c.runs_conceded / c.wickets
             WHEN c.wickets IS NULL THEN c.reported_bowling_average
        END AS bowling_average,
        CASE WHEN c.legal_balls_bowled > 0
                  THEN 6.0 * c.runs_conceded / c.legal_balls_bowled
             WHEN c.legal_balls_bowled IS NULL THEN c.reported_economy
        END AS economy_rate
    FROM v_latest_career AS c
    JOIN formats AS f ON f.format_id = c.format_id
    JOIN sources AS s ON s.source_id = c.source_id
    WHERE s.name = :source_name AND c.scope = 'career'
), component_points AS (
    SELECT player_id, format_id, cricket_format,
        runs * 0.01 + batting_average * 0.5 + strike_rate * 0.3 AS batting_points,
        wickets * 2.0 + (50.0 - bowling_average) * 0.5
            + (6.0 - economy_rate) * 2.0 AS bowling_points,
        catches * 3.0 + stumpings * 5.0 AS fielding_points
    FROM career_metrics
    WHERE runs IS NOT NULL AND wickets IS NOT NULL
      AND catches IS NOT NULL AND stumpings IS NOT NULL
      AND batting_average IS NOT NULL AND strike_rate IS NOT NULL
      AND bowling_average IS NOT NULL AND economy_rate IS NOT NULL
), scored_players AS (
    SELECT *, batting_points + bowling_points + fielding_points AS total_points
    FROM component_points
), ranked_players AS (
    SELECT *, DENSE_RANK() OVER (
        PARTITION BY format_id ORDER BY total_points DESC
    ) AS performance_rank
    FROM scored_players
)
SELECT r.cricket_format, r.performance_rank, p.full_name AS player_name,
    ROUND(r.batting_points, 2) AS batting_points,
    ROUND(r.bowling_points, 2) AS bowling_points,
    ROUND(r.fielding_points, 2) AS fielding_points,
    ROUND(r.total_points, 2) AS total_points
FROM ranked_players AS r
JOIN players AS p ON p.player_id = r.player_id
ORDER BY r.cricket_format ASC, r.performance_rank ASC, p.player_id ASC;
