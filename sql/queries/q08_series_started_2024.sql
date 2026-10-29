-- Q08: One display row per series starting in calendar year 2024 (SQLite).
SELECT
    s.name AS series_name,
    (
        SELECT GROUP_CONCAT(h.name, ', ')
        FROM (
            SELECT c.name
            FROM series_hosts AS sh
            JOIN countries AS c ON c.country_id = sh.country_id
            WHERE sh.series_id = s.series_id
            ORDER BY c.name, c.country_id
        ) AS h
    ) AS host_country,
    (
        SELECT GROUP_CONCAT(ft.code, ', ')
        FROM (
            SELECT f.code
            FROM series_formats AS sf
            JOIN formats AS f ON f.format_id = sf.format_id
            WHERE sf.series_id = s.series_id
            ORDER BY f.code, f.format_id
        ) AS ft
    ) AS match_type,
    s.start_date,
    s.planned_matches AS total_matches_planned
FROM series AS s
WHERE s.start_date >= '2024-01-01'
  AND s.start_date < '2025-01-01'
ORDER BY s.start_date ASC, s.series_id ASC;
