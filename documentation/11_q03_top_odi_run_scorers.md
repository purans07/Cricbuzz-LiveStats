# Phase 11 — Question 3: top ten ODI career run scorers

## Business problem

The exact brief asks: “List the top 10 highest run scorers in ODI cricket. Show player name, total runs scored, batting average, and number of centuries. Display the highest run scorer first.” This is a career batting leaderboard, not a ranking based on the small set of scorecards we happened to import.

## Concepts, tables and relationships before the query

Use joins to resolve player, format and source names; WHERE to select ODI career data; CASE for the batting-average denominator; ROUND and real-number arithmetic; ORDER BY for ranking; and LIMIT for the first ten results.

`career_stats_snapshots.player_id` references `players.player_id`; `format_id` references `formats.format_id`; `batch_id` references `import_batches.batch_id`, which carries `source_id` referencing `sources.source_id`. The existing `v_latest_career` view joins those batch records and excludes deleted players. It retains the latest committed snapshot per player/format/source by fetched_at, breaking timestamp ties using the higher batch ID. Failed and pending batches do not qualify. The view uses an anti-existence check for a newer eligible snapshot, so no new window function or schema change is needed here.

## Query logic and execution strategy

Choose one source explicitly. Use its latest committed career record for each ODI player. Do not add old and new career snapshots: they are successive measurements of overlapping careers, not disjoint innings. Do not calculate career totals from our incomplete batting_performances history.

For a positive known dismissal count, batting average = runs / dismissals. Unknown dismissals permit the separately stored provider-reported average as a fallback; this has different provenance from a recalculation. Zero dismissals means undefined average, even if a provider prints a numeric placeholder. Match appearances and batting innings are not the average denominator. Missing centuries remain NULL rather than being invented as zero.

Exclude unknown run totals. Sort by runs descending, then player ID ascending, and return at most ten rows. This chooses ten people rather than all people tied at tenth place. Identical names are not merged. The source parameter prevents adding or mixing measurements from separate providers.

Conceptually: select the ODI/source scope, choose latest committed rows, resolve player names, compute averages, sort, then keep ten. The physical optimizer can reorder joins; its measured behavior is recorded below.

## SQL query

```sql
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
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment identifies the ranking and source scope. |
| 2 | Comment specifies the source-name parameter and warns against summing snapshots. |
| 3 | Begin the output projection. |
| 4 | Return the profile name under the player_name alias. |
| 5 | Return the latest known career runs as total_runs. |
| 6 | Begin conditional selection of batting average. |
| 7 | Use a calculated average when dismissals are positive. |
| 8 | Multiply by 1.0 to avoid integer division, divide runs by dismissals, then round to two decimals. |
| 9 | If the dismissal denominator is unknown, consider the separately stored provider average. |
| 10 | Return that reported value; it remains NULL if not supplied. |
| 11 | An explicit zero-dismissal career has an undefined batting average, represented by NULL. |
| 12 | End the conditional expression and label its result batting_average. |
| 13 | Return the number of career centuries, preserving unknown values. |
| 14 | Read the existing latest-committed-career view. |
| 15 | Join the player identity to obtain the name; the view already excludes deleted players. |
| 16 | Join the format identity to select ODI specifically. |
| 17 | Join the import source identity to keep provider/training-source scope explicit. |
| 18 | Only the ODI format qualifies; Test and T20 records are not combined. |
| 19 | Explicitly require career scope rather than series totals. |
| 20 | Select exactly the bound source name without concatenating it into SQL. |
| 21 | Exclude unknown run totals because they cannot be ranked; known zero remains eligible. |
| 22 | Sort highest runs first; use player ID ascending for a stable ordering of ties. |
| 23 | Return at most ten players, even if more are tied at the cutoff. |

## Running it with bound parameters

Load `sql/queries/q03_top_odi_run_scorers.sql` and execute through a read transaction using SQLAlchemy `text(query)` and one bound parameter:

- Sample source_name: `Synthetic training fixture`.
- Live source_name: `cricketapilive-cricbuzz-cricket/v2/provider`.

A nonexistent source returns no rows. Do not interpolate a source name into the SQL. This question uses the latest stored snapshots, with no historical as-of filter. It does not claim that all players were fetched simultaneously or that their snapshot dates match. The existing view intentionally keeps the newest partial snapshot; if its runs are unknown, do not silently substitute an older larger total.

## Observed results

Complete outputs, parameters and plans are recorded in `11_q03_result.json`.

| Dataset | Returned rows | First row |
| --- | --- | --- |
| Synthetic sample | 10 | Sample Player 12 — 2,980 runs; 57.31 average; 2 centuries |
| Stored live data | 1 | Temba Bavuma — 2,168 runs; 43.36 average; 6 centuries |

The sample population is fictional. The live database currently contains ODI career data for only one enriched player. Its one-row output does not establish Bavuma as a global leading run scorer. LIMIT 10 means up to ten known eligible records, not a promise of ten available or globally representative players. No API refresh is performed by this query.

## Actual SQLite execution plan

Both working databases used the unique format-code and source-name indexes to resolve ODI and the selected source. `idx_career_format_player` searched career snapshots by format ID. Batch rows were resolved by primary key. Inside the latest-snapshot view, SQLite used the source/fetch-time index for the newer-batch checks and the player/format/batch uniqueness index to locate corresponding snapshots. Player names were resolved through their primary keys. A temporary B-tree sorted the output before the limit.

The plan exposes two player lookups: the active-player lookup inside the existing view and the outer name lookup. This is the observed SQLite plan for the current small datasets. No claim is made about PostgreSQL/MySQL execution or about constant query time.

## Optimization

Reuse the established latest-snapshot view rather than repeating snapshot-selection logic differently in every leaderboard. Keep format and source filters explicit; the existing indexes support these identities and the anti-existence lookup. Multiplying by 1.0 avoids truncation of integer division. ORDER BY c.runs uses full integer run totals; rounding the displayed average cannot alter ranking.

LIMIT does not eliminate the work of identifying eligible latest snapshots or sorting candidates. An index on a historical runs column alone would not establish which snapshot is current. Do not add such an index as an assumed fix. At larger scale, measure the view and final sorting with representative data before considering a maintained current-snapshot projection or alternative latest-row strategy. No new index or schema change was justified here.

## Verification and checkpoint

The full suite passes **232 tests**; lint, formatting and whitespace checks pass. Six dedicated tests check top-ten shape/order; newer snapshots rather than maximum historical totals; failed-batch exclusion; zero/unknown denominators and reported-average fallback; NULL runs/centuries; deleted profiles; format and source isolation; bound hostile-looking input; latest-batch timestamp ties; equal-run ordering; and distinct players with identical names. All test mutations occur in temporary database copies. Working datasets were read without modification, and no API requests were used.

Question 3 is complete. Question 4 has not been implemented. Say **NEXT** to proceed to Question 4.
