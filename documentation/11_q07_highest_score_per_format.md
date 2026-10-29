# Phase 11 — Question 7: highest individual score per format

## Business problem

The exact brief asks: “Find the highest individual batting score achieved in each cricket format (Test, ODI, T20I). Display the format and the highest score for that format.” This compares individual batting peaks across the three named international formats.

## Concepts, tables and relationships before SQL

Use MAX to find the largest individual score, GROUP BY to return one result per format, LEFT JOIN to retain requested formats with missing data, and a CTE with VALUES to enumerate the three requested categories. A CTE names a temporary query result; it does not create a persistent table. A scalar subquery resolves one selected source by its unique name.

`formats` identifies the format and its level. `career_stats_snapshots.highest_score` stores each player's career-best individual innings score; it is not their career runs total. The existing `v_latest_career` view selects the latest committed snapshot for each player/format/source and excludes deleted profiles. Source comes through the snapshot's import batch and references `sources.source_id`.

## Query logic and execution strategy

Create the three requested format labels, resolve exact international format codes, attach latest career records from one selected source, group by format and find MAX(highest_score). If a format, source or all scores are absent, keep its row with NULL rather than displaying zero.

MAX ignores individual NULL values; if every value is NULL (or there are no matches), its result is NULL. A genuine known zero score remains zero. Do not SUM career runs, average individual high scores, add successive snapshots, or infer an all-time record from our small scorecard collection. Here the source is career highest-score data, not `batting_performances`. Local scorecard overrides do not automatically rewrite independent provider career snapshots.

Use the latest eligible snapshot even if its highest_score is unknown; do not silently substitute an older value. The selected-source maximum is over stored profiles, not a proof that all professional players were imported. This query uses latest stored snapshots, not a historical as-of date.

T20I must match code T20I exactly. IPL, domestic T20 and the provider bucket INTERNATIONAL_T20 are excluded. Our importer has not established official T20I eligibility for that ambiguous bucket, so relabeling it would overstate the evidence.

The expected logical process is three category rows, format/source resolution, eligible career snapshot selection, aggregation and ordering. The actual physical plan is measured below.

## SQL query

```sql
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
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment defines the selected-source career scope, without claiming a worldwide record. |
| 2 | Define a CTE: a named temporary result containing the requested labels, stored format codes and output order. |
| 3 | Create three constant rows for Test, ODI and T20I. These are requested categories, not fabricated scores. |
| 4 | End the CTE definition. |
| 5 | Begin the output projection. |
| 6 | Return the readable requested format label. |
| 7 | Take the maximum known individual career highest score in that format. |
| 8 | Start from the three requested format rows so missing data does not remove a format. |
| 9 | Look up each requested format in the stored catalogue, preserving missing formats. |
| 10 | Match the exact format code and require international classification. |
| 11 | Attach eligible latest career snapshots without removing empty categories. |
| 12 | Match the snapshot to its resolved format identity. |
| 13 | Restrict snapshots to the selected source through a scalar source-ID lookup. |
| 14 | Find that source ID by its unique name, supplied as a bound parameter. |
| 15 | End the source lookup. A missing source matches no snapshots. |
| 16 | Require career scope, not a series aggregate. |
| 17 | Produce one maximum per requested format and its explicit output order. |
| 18 | Return Test, ODI, T20I in that order and terminate the SQL statement. |

## Running it and observed results

Load `sql/queries/q07_highest_score_per_format.sql` and execute SQLAlchemy `text(query)` inside an existing read transaction with a bound source_name:

- Sample: `Synthetic training fixture`.
- Live: `cricketapilive-cricbuzz-cricket/v2/provider`.

The unique source-name constraint ensures the lookup resolves at most one source ID. A missing or unrecognized source produces the three requested rows with NULL scores. No untrusted input is concatenated into the statement.

| Format | Fictional sample maximum | Limited live maximum |
| --- | ---: | ---: |
| Test | 172 | 179 |
| ODI | 172 | 144 |
| T20I | 172 | NULL |

The sample uses simplified synthetic data with the same maximum across formats. The live career population contains one enriched player, Temba Bavuma. His stored Test and ODI highest scores supply those live values. They are **not worldwide records**. T20I is NULL because no verified T20I career snapshot has been imported; ambiguous T20 data is deliberately excluded.

Complete outputs, exact source parameters and measured plans are in `11_q07_result.json`. Working databases were read without changes, and no API request was used.

## Actual SQLite plan

On both working datasets, SQLite reads the three constant CTE rows using a co-routine and materializes the latest-career view. It scans career snapshots, resolves their batches/active players through primary keys, and uses the unique source-name index for the selected-source lookup. The latest-snapshot anti-existence logic uses source/fetch-time and player/format/batch indexes to test newer eligible records.

The outer query resolves each requested format using the unique format-code index and LEFT JOINs the materialized career rows. Temporary B-trees support GROUP BY and the explicit final order. The exact plan is preserved in the JSON report. This observed plan does not claim an indexed highest_score range scan or PostgreSQL/MySQL verification.

## Optimization

Only two output columns are needed; player names and match joins are unnecessary. Keep exact format/source predicates and use MAX rather than sorting all individual scores and attempting a per-format LIMIT. Keep snapshot eligibility inside the LEFT JOIN, because an outer WHERE on those columns could discard missing-format rows. Missing values are meaningful, so do not apply COALESCE(highest_score,0) as a supposed optimization.

The view materialization is acceptable for the current small population. At larger scale, benchmark a scoped pre-aggregation or maintained current-career projection before changing the view or adding indexes. An index over historical highest_score alone does not identify current snapshots, and the three constant category rows are not a performance bottleneck. No schema or index change was introduced.

The CTE/VALUES syntax and measured plan are validated on SQLite only. Porting this three-category construction to another database requires dialect verification under the project's existing portability policy.

## Verification and checkpoint

The full suite passes **251 tests**; lint, formatting and whitespace checks pass. Five focused tests cover maximum individual scores rather than sums; latest committed snapshots and deleted profiles; NULL versus genuine zero; missing format rows and ambiguous T20 exclusion; source isolation and bound hostile-looking input. All test mutations occur in temporary database copies.

Question 7 is complete. Question 8 has not been implemented. Say **NEXT** to proceed to Question 8.
