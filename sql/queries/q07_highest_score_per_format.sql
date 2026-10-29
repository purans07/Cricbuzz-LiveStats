-- Q07: Highest individual career score among known players of one source.
WITH requested_formats (format, format_code, sort_order) AS (
    VALUES ('Test', 'TEST', 1), ('ODI', 'ODI', 2), ('T20I', 'T20I', 3)
)
SELECT
    rf.format,
    MAX(c.highest_score) AS highest_score
FROM requested_formats AS rf
LEFT JOIN formats AS f
    ON f.code = rf.format_code AND f.level = 'international'
LEFT JOIN v_latest_career AS c
    ON c.format_id = f.format_id
   AND c.source_id = (
       SELECT source_id FROM sources WHERE name = :source_name
   )
   AND c.scope = 'career'
GROUP BY rf.format, rf.sort_order
ORDER BY rf.sort_order;
