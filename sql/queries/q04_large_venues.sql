-- Q04: Venues with known capacity strictly greater than 50,000.
SELECT
    v.name AS venue_name,
    v.city,
    c.name AS country,
    v.capacity
FROM venues AS v
LEFT JOIN countries AS c ON c.country_id = v.country_id
WHERE v.capacity > 50000
ORDER BY v.capacity DESC, v.venue_id ASC;
