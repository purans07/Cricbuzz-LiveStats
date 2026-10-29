-- Q14: Venue bowling over at least three matches with >= 24 legal balls each.
WITH qualifying_matches AS (
    SELECT
        b.player_id,
        b.match_id,
        m.venue_id,
        CASE WHEN COUNT(*) = COUNT(b.runs_conceded)
             THEN 6.0 * SUM(b.runs_conceded) / SUM(b.legal_balls)
        END AS match_economy,
        CASE WHEN COUNT(*) = COUNT(b.wickets)
             THEN SUM(b.wickets)
        END AS match_wickets
    FROM v_active_bowling AS b
    JOIN matches AS m ON m.match_id = b.match_id
    WHERE m.venue_id IS NOT NULL
    GROUP BY b.player_id, b.match_id, m.venue_id
    HAVING COUNT(*) = COUNT(b.legal_balls)
       AND SUM(b.legal_balls) >= 24
)
SELECT
    p.full_name AS player_name,
    v.name AS venue_name,
    CASE WHEN COUNT(*) = COUNT(q.match_economy)
         THEN ROUND(AVG(q.match_economy), 2)
    END AS average_economy_rate,
    CASE WHEN COUNT(*) = COUNT(q.match_wickets)
         THEN SUM(q.match_wickets)
    END AS total_wickets,
    COUNT(*) AS matches_played
FROM qualifying_matches AS q
JOIN players AS p ON p.player_id = q.player_id
JOIN venues AS v ON v.venue_id = q.venue_id
GROUP BY p.player_id, p.full_name, v.venue_id, v.name
HAVING COUNT(*) >= 3
ORDER BY p.full_name ASC, v.name ASC, p.player_id ASC, v.venue_id ASC;
