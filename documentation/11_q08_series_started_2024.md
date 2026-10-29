# Phase 11 — Question 8: series starting in 2024

## Business problem

The exact brief asks: “Show all cricket series that started in the year 2024. Include series name, host country, match type, start date, and total number of matches planned.” This provides the stored 2024 competition schedule and planned scope.

## Concepts, tables and relationships before SQL

Use a half-open date range, correlated scalar subqueries, ordered display aggregation with GROUP_CONCAT, joins by foreign keys, and deterministic ORDER BY.

`series` stores series_id, name, start_date and planned_matches. `series_hosts` links series_id to one or more countries; `countries` supplies host names. `series_formats` links series_id to one or more formats; `formats` supplies match-type codes. Both linking tables have composite primary keys, preventing repeated identical associations.

Host country means the explicit series host relationship. It is not inferred from a team's country, a series title or one match venue. Match type means the stored series format code. Planned matches comes from series metadata, not COUNT of available match rows.

## Logic and execution strategy

Select series whose start_date is at least 2024-01-01 and less than 2025-01-01. A series starting in 2023 and continuing into 2024 does not qualify. NULL start dates cannot establish eligibility and are excluded. Dates follow the established ISO YYYY-MM-DD representation.

Return one row per series. Independently collect its alphabetically sorted host names and format codes, then concatenate each collection for display. This avoids joining two one-to-many relationships together: two hosts and three formats would otherwise produce six rows for the same series. The planned match count must not be multiplied or summed over those combinations.

Unknown hosts, formats and planned counts stay NULL. A genuine planned count of zero stays zero. Comma-separated values exist only in this query's display result; the underlying relational tables remain normalized. Separate IDs preserve distinct same-named series.

The expected access path is a start-date range search followed by indexed relationship lookups and small host/format sorts. The actual measured plan appears below.

## SQL query

```sql
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
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment defines one output row per stored series and the SQLite dialect. |
| 2 | Begin the selected output fields. |
| 3 | Return the series name. |
| 4 | Begin a scalar subquery for this series’s host-country display list. |
| 5 | Concatenate host names with a comma and space; no input rows produces NULL. |
| 6 | Begin the ordered host-row subquery. |
| 7 | Select each country name. |
| 8 | Read series-host relationships. |
| 9 | Resolve each relationship to its country name. |
| 10 | Correlate host relationships with the current outer series ID. |
| 11 | Sort hosts alphabetically, then by country ID. |
| 12 | Name the ordered host rows h. |
| 13 | End the scalar subquery and label the resulting display column host_country. |
| 14 | Begin a separate scalar subquery for the match-format list. |
| 15 | Concatenate format codes, using the same readable separator. |
| 16 | Begin the ordered format-row subquery. |
| 17 | Select the stored format code, such as ODI, TEST or T20I. |
| 18 | Read series-format relationships. |
| 19 | Resolve those relationships to format codes. |
| 20 | Correlate formats with the current series ID. |
| 21 | Sort codes alphabetically, then by format ID. |
| 22 | Name the ordered format rows ft. |
| 23 | End the scalar subquery and label its result match_type. |
| 24 | Return the stored start date. |
| 25 | Return the planned match total under the requested display alias. |
| 26 | Read series as the outer relation, retaining one row per series identity. |
| 27 | Include starts on or after 1 January 2024. |
| 28 | Exclude starts on or after 1 January 2025. |
| 29 | Sort chronologically; series ID breaks same-date ties deterministically. |

## Running it and actual output

Load `sql/queries/q08_series_started_2024.sql` and execute SQLAlchemy `text(query)` inside an existing read transaction. There are no input parameters: 2024 is fixed by the question, not a relative year. Venue or match history is not needed to run it.

| Fictional sample series | Host | Match types | Start date | Planned matches |
| --- | --- | --- | --- | ---: |
| Synthetic series 2024 Q1 | India | ODI, T20I, TEST | 2024-01-01 | 6 |
| Synthetic series 2024 Q2 | Australia | ODI, T20I, TEST | 2024-04-01 | 6 |
| Synthetic series 2024 Q3 | India | ODI, T20I, TEST | 2024-07-01 | 6 |
| Synthetic series 2024 Q4 | Australia | ODI, T20I, TEST | 2024-10-01 | 6 |

The live database returns no rows. Its three stored series do not start in 2024; historical 2024 archives have not been imported. Empty output is not evidence that no real series began in 2024. No archive fetch or guessed metadata was used.

The query covers the selected database's stored series inventory, retaining source-scoped identities separately. It does not claim worldwide historical completeness or deduplication across providers. Complete outputs and plans are in `11_q08_result.json`.

## Actual SQLite execution plan

Both working databases show `SEARCH s USING INDEX idx_series_start (start_date>? AND start_date<?)`. Each correlated host/format subquery uses the corresponding relationship primary-key index on series_id, then primary-key lookups for countries or formats. SQLite sorts those small display lists with temporary B-trees and consumes them through co-routines.

The outer chronological order follows the chosen access path; the observed plan shows no extra final sort. That is a measurement on these datasets, not a universal optimizer guarantee. The full raw plan is recorded in the JSON result.

## Optimization

Keep the range comparison directly on start_date. A year-extraction function on the column can prevent the existing date index from supporting a simple range search. Half-open boundaries express the exact calendar year and also avoid a time-of-day end-boundary mistake if date handling is later generalized.

Do not join hosts and formats in a single flat result then SUM planned_matches: that changes the output grain and inflates totals. Independent aggregations preserve one series row and nullable metadata. Existing foreign-key relationship indexes support series-ID lookups. DISTINCT is unnecessary because each host/format association is already unique.

For a larger series inventory, benchmark pre-aggregating hosts and formats for eligible series against correlated lookups before rewriting. Ordered concatenation has a cost, but the current relationship lists are small. No new index or schema change is justified here.

GROUP_CONCAT, its nested ordered inputs and the observed plan are tested on SQLite. PostgreSQL typically needs STRING_AGG and MySQL has different ordered aggregation syntax. Those dialects are not claimed to work unchanged. Display lists can contain commas in a name; this is a human-readable result, not an interchange format to split back into identities.

## Verification and checkpoint

The full suite passes **256 tests**; lint, formatting and whitespace checks pass. Five focused tests cover inclusive 2024 start/exclusive 2025 boundary, NULL dates, multi-host/multi-format lists without row multiplication, unknown metadata despite imported match rows, zero planned matches, same-named series identities, and series overlapping 2024 but beginning in 2023. All modifications occur in temporary test databases; working datasets were read without changes. No API request was used.

Question 8 completes the brief's eight beginner questions. Questions 9–25 remain pending. Say **NEXT** to start Question 9; Phase 11 is not yet complete.
