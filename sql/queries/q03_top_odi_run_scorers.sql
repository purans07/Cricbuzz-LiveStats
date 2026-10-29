-- Q03: Top ten known ODI career run totals from one selected source.
-- Bind source_name; the latest stored snapshot is used, not a sum of snapshots.
SELECT
    p.full_name AS player_name,
    c.runs AS total_runs,
    CASE
        WHEN c.dismissals > 0
            THEN ROUND(1.0 * c.runs / c.dismissals, 2)
        WHEN c.dismissals IS NULL
            THEN c.reported_batting_average
        ELSE NULL
    END AS batting_average,
    c.centuries
FROM v_latest_career AS c
JOIN players AS p ON p.player_id = c.player_id
JOIN formats AS f ON f.format_id = c.format_id
JOIN sources AS s ON s.source_id = c.source_id
WHERE f.code = 'ODI'
  AND c.scope = 'career'
  AND s.name = :source_name
  AND c.runs IS NOT NULL
ORDER BY c.runs DESC, p.player_id ASC
LIMIT 10;
