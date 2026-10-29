-- Q26: Source-separated saved match coverage; not a worldwide match count.
-- COUNT(DISTINCT) prevents innings joins from multiplying match totals.
SELECT
    s.name AS source_name,
    f.code AS format,
    m.status AS saved_status,
    COUNT(DISTINCT m.match_id) AS saved_matches,
    COUNT(DISTINCT i.innings_id) AS saved_innings,
    COUNT(DISTINCT CASE WHEN i.innings_id IS NOT NULL THEN m.match_id END)
        AS matches_with_innings,
    MIN(m.starts_at) AS earliest_match,
    MAX(m.starts_at) AS latest_match
FROM matches AS m
JOIN sources AS s ON s.source_id = m.source_id
JOIN formats AS f ON f.format_id = m.format_id
LEFT JOIN innings AS i ON i.match_id = m.match_id
GROUP BY s.source_id, s.name, f.format_id, f.code, m.status
ORDER BY s.name, f.code, m.status;
