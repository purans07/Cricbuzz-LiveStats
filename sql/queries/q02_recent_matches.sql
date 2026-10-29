-- Q02: Matches started within a rolling 30-day UTC window.
-- Bind window_start and as_of_utc as canonical UTC timestamps.
SELECT
    m.description AS match_description,
    t1.name AS team1_name,
    t2.name AS team2_name,
    v.name AS venue_name,
    v.city AS venue_city,
    m.starts_at AS match_date
FROM matches AS m
JOIN match_teams AS mt1 ON mt1.match_id = m.match_id AND mt1.slot = 1
JOIN teams AS t1 ON t1.team_id = mt1.team_id
JOIN match_teams AS mt2 ON mt2.match_id = m.match_id AND mt2.slot = 2
JOIN teams AS t2 ON t2.team_id = mt2.team_id
LEFT JOIN venues AS v ON v.venue_id = m.venue_id
WHERE m.starts_at >= :window_start
  AND m.starts_at <= :as_of_utc
  AND m.status IN ('completed', 'live', 'abandoned')
  AND (
      m.status = 'completed'
      OR EXISTS (
          SELECT 1 FROM innings AS i
          WHERE i.match_id = m.match_id AND i.legal_balls > 0
      )
  )
ORDER BY m.starts_at DESC, m.match_id DESC;
