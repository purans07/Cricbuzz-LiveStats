# Phase 11 — Question 4: venues seating more than 50,000

## Business problem

The project brief asks: “Display all cricket venues that have a seating capacity of more than 50,000 spectators. Show venue name, city, country, and capacity. Order by largest capacity first.” This identifies large venues from the stored inventory.

## Concepts, tables and relationships before SQL

Use SELECT for the requested columns, LEFT JOIN to resolve an optional country name, WHERE with a strict numeric comparison, and ORDER BY DESC for largest-first results.

`venues` contains venue_id, name, city, country_id and capacity. `venues.country_id` references `countries.country_id`, whose name is the requested country label. A country or city can be unknown. Keep a qualifying venue even when its country cannot be resolved; an inner join would unnecessarily remove that venue.

## Logic and planned execution

Read venues, retain those with a known integer capacity greater than 50,000, resolve any country name, and order by descending capacity. Use venue_id ascending as a stable tie-breaker. Exactly 50,000 does not qualify. NULL does not satisfy the comparison, so unknown capacities are excluded without treating them as zero. Return all qualifying stored venue identities, without a top-N limit.

The expected small-table plan is a venue scan, primary-key country lookups and a final sort. The measured plan is recorded below rather than assumed to prove index use.

## SQL query

```sql
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
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states the question and strict threshold. |
| 2 | Begin selecting output columns. |
| 3 | Return venue name with the clear alias venue_name. |
| 4 | Return the stored city, retaining NULL if unknown. |
| 5 | Return the joined country name as country. |
| 6 | Return the numeric seating capacity. |
| 7 | Read venues with the short alias v. |
| 8 | Resolve the country by ID, keeping the venue if country is unknown. |
| 9 | Require capacity strictly greater than 50,000. NULL comparisons are unknown and therefore do not pass WHERE. |
| 10 | Sort largest first; stable venue-ID order resolves equal capacities. End the statement. |

## Running the query and observed output

Load `sql/queries/q04_large_venues.sql` and execute it with SQLAlchemy `text(query)` inside an existing read transaction. It has no input parameters because 50,000 is the fixed threshold in the brief. Do not convert capacity to formatted text such as “60,000” before comparison; the schema stores a nonnegative integer.

The unchanged sample returns one fictional venue:

| venue_name | city | country | capacity |
| --- | --- | --- | ---: |
| Sample Ground 1 | Sample City 1 | India | 60000 |

The live database returns no rows. All four stored live venues have NULL capacity because the tested match-list/scorecard responses do not provide it. That result describes missing capacity coverage, not a conclusion about the real seating capacities of those grounds. No capacity was guessed and no API request was used.

The query is over the selected database's entire stored inventory, without an additional provider filter. Distinct source-scoped venue records remain separate; identical names are not proof that two records describe the same physical stadium. Globally deduplicated or globally complete venue coverage is not claimed.

## Measured SQLite execution plan

Both working databases report:

1. `SCAN v`: read venues and apply the capacity filter.
2. `SEARCH c USING INTEGER PRIMARY KEY ... LEFT-JOIN`: resolve countries when present.
3. `USE TEMP B-TREE FOR ORDER BY`: sort qualifying rows.

Complete outputs and actual plans are saved in `11_q04_result.json`. No index on capacity currently exists. The country foreign-key index serves other access paths; it does not turn this capacity filter into an indexed range search. PostgreSQL/MySQL plans are not verified.

## Optimization

Keep the integer column directly in `capacity > 50000`; avoid applying string formatting, CAST or COALESCE to that indexed candidate expression. NULL already has the correct exclusion behavior. LEFT JOIN retains known-capacity venues even with incomplete location metadata. Avoid DISTINCT, which could collapse separate same-named venues or add unnecessary duplicate-removal work.

The sample has two venues and the live database has four, so a scan is reasonable. No new index is justified by these tiny tables. With a large representative venue inventory and repeated queries, benchmark a capacity/venue-ID index and inspect whether it reduces filtering/sort costs before changing the schema. Mixed sorting directions and optimizer choices must be verified rather than assuming that any capacity index removes the sort.

## Verification and checkpoint

The full suite passes **236 tests**; lint, formatting and whitespace checks pass. Four dedicated tests cover capacities 49,999, 50,000, 50,001 and NULL; optional city/country; country resolution and descending capacity; stable equal-capacity ordering without merging same-named identities; and no qualifying rows. All mutations occur in temporary database copies. Working databases were read only.

Question 4 is complete. Question 5 has not been implemented. Say **NEXT** for Question 5.
