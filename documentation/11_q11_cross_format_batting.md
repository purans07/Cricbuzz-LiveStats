# Phase 11 — Question 11: cross-format batting comparison

## Business problem

The exact brief asks: “Compare each player's performance across different cricket formats. For players who have played at least 2 different formats, show their total runs in Test cricket, ODI cricket, and T20I cricket, along with their overall batting average across all formats.” This creates a player comparison with one run column per requested format.

## Definitions before implementation

For this lesson, “formats” and “overall” refer to the three requested international categories: Test, ODI and verified T20I. At least two of those categories must have a latest selected-source career row with matches_played > 0. IPL or ambiguous T20 classifications do not establish eligibility. This is a scoped interpretation of the question, not a claim about every domestic/league format in a player's career.

Overall average is pooled runs / pooled dismissals across the player's evidenced played target-format rows. It is not the average of format averages. Example: 100 runs/1 dismissal and 900 runs/30 dismissals gives 1000/31 = 32.26, not (100+30)/2 = 65.

An unrepresented third format has NULL runs, not fabricated zero. That can mean not played or insufficient coverage; this pivot alone does not distinguish the causes. If an included played format has unknown runs or dismissals, overall average is NULL rather than calculated from a subset of that player's eligible rows. If total dismissals are zero, the average is undefined and stays NULL. Missing-format coverage still limits how broadly the combined known-format average can be interpreted.

## SQL concepts, tables and relationships

Use a CTE for eligible career rows; CASE for conditional aggregation (a portable-style pivot); MAX to select each format's single latest runs value; SUM for combined numerators/denominators; COUNT for completeness checks; NULLIF for safe zero-denominator handling; GROUP BY for one row per player; and HAVING for the post-aggregation minimum format count.

`v_latest_career` supplies one committed current record per player/format/source, excluding deleted players and failed/pending batches. `players` supplies identity/name; `formats` supplies code/level; `sources` identifies the selected snapshot origin. The latest view orders snapshot eligibility by fetched_at and batch ID, not maximum runs. This query does not add successive snapshots, infer appearances from nonzero scores or use incomplete imported match totals as career totals.

## Logic and execution strategy before SQL

Choose one source and the three requested international format codes. Keep rows with positive career match appearances. Group them by player identity. Use MAX(CASE...) to place each latest run total under its format column. Compute the combined average only when runs/dismissals are complete across those included rows, then require at least two distinct eligible formats with HAVING.

MAX here does not select a player's highest career snapshot or innings score; latest-row selection has already occurred. With one row per format, MAX simply extracts that format's run value from the grouped rows. There is no ELSE 0, so a missing format stays NULL while an explicitly recorded zero remains zero.

The logical stages are source/format/appearance filtering, latest-snapshot eligibility, player grouping/pivot, completeness/average calculation, HAVING, and final name ordering. The optimizer determines the physical order; its measured plan appears below.

## SQL query

```sql
-- Q11: Compare players with evidenced appearances in at least two target formats.
WITH eligible_careers AS (
    SELECT p.player_id, p.full_name, f.code, c.runs, c.dismissals
    FROM v_latest_career AS c
    JOIN players AS p ON p.player_id = c.player_id
    JOIN formats AS f ON f.format_id = c.format_id
    JOIN sources AS s ON s.source_id = c.source_id
    WHERE s.name = :source_name
      AND c.scope = 'career'
      AND f.code IN ('TEST', 'ODI', 'T20I')
      AND f.level = 'international'
      AND c.matches_played > 0
)
SELECT
    player_id,
    full_name AS player_name,
    MAX(CASE WHEN code = 'TEST' THEN runs END) AS test_runs,
    MAX(CASE WHEN code = 'ODI' THEN runs END) AS odi_runs,
    MAX(CASE WHEN code = 'T20I' THEN runs END) AS t20i_runs,
    CASE
        WHEN COUNT(*) = COUNT(runs) AND COUNT(*) = COUNT(dismissals)
        THEN ROUND(1.0 * SUM(runs) / NULLIF(SUM(dismissals), 0), 2)
        ELSE NULL
    END AS overall_batting_average
FROM eligible_careers
GROUP BY player_id, full_name
HAVING COUNT(DISTINCT code) >= 2
ORDER BY full_name ASC, player_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment defines eligibility in the three target formats using actual career appearance evidence. |
| 2 | Create a CTE to name the selected latest career rows before pivoting. |
| 3 | Select stable player ID, name, format code, runs and dismissals. |
| 4 | Read the latest committed career view, which excludes deleted players. |
| 5 | Resolve the profile name and identity. |
| 6 | Resolve the format code and classification. |
| 7 | Resolve the source identity. |
| 8 | Keep only the bound selected source. |
| 9 | Require career scope, not series totals. |
| 10 | Restrict comparison to Test, ODI and verified T20I codes. |
| 11 | Require international classification. |
| 12 | Require positive recorded match appearances; zero or unknown does not establish participation. |
| 13 | End the eligible-career CTE. |
| 14 | Begin the final output projection. |
| 15 | Return the stable local player ID for distinguishing same-named people. |
| 16 | Return player name. |
| 17 | Place Test runs in their own column. Non-Test rows contribute NULL. |
| 18 | Place ODI runs in their own column. |
| 19 | Place verified T20I runs in their own column. |
| 20 | Begin conditional calculation of the overall batting average. |
| 21 | Calculate only if all eligible rows have known runs and known dismissals. |
| 22 | Divide summed runs by summed dismissals using real arithmetic; NULLIF avoids zero division, then round to two decimals. |
| 23 | Otherwise preserve unknown as NULL rather than presenting a partial calculation. |
| 24 | End the expression and name its result. |
| 25 | Read the selected career rows. |
| 26 | Aggregate by player identity/name to preserve separate people with identical names. |
| 27 | After aggregation, retain only players with at least two different eligible format codes. |
| 28 | Sort names alphabetically, then IDs for stable same-name ties. |

## Running it and measured output

Load `sql/queries/q11_cross_format_batting.sql` and execute SQLAlchemy `text(query)` within an existing read transaction. Bind source_name to `Synthetic training fixture` or `cricketapilive-cricbuzz-cricket/v2/provider`. A missing source yields no comparison rows. Parameter values must not be concatenated into SQL.

The sample returns 12 fictional players. Sample Player 01 has 1,660 runs in each synthetic format and an overall average of 40.49; the repeated per-format totals are deliberate seed simplifications, not realistic professional records.

The live result is:

| Player | Test runs | ODI runs | T20I runs | Combined known-format average |
| --- | ---: | ---: | --- | ---: |
| Temba Bavuma | 3993 | 2168 | NULL | 40.27 |

The average is (3993+2168)/(103+50) = 6161/153, rounded to 40.27. It covers verified Test/ODI records only. The unverified INTERNATIONAL_T20 bucket is not relabeled T20I or included in the denominator. One enriched profile is not a globally complete player-comparison population.

The local player ID is returned alongside the requested comparison fields to distinguish same-named identities. No as-of historical date is supplied: this uses latest stored snapshots and does not guarantee identical capture times across players. Full output, exact source parameters and plans are in `11_q11_result.json`.

## Actual SQLite execution plan

Both databases used the unique source-name and format-code indexes, `idx_career_format_player` for format-scoped career candidates, and primary keys for batches/players. The latest-snapshot anti-existence check used the source/fetch-time and player/format/batch indexes. SQLite used temporary B-trees for GROUP BY, COUNT(DISTINCT) and final ordering.

The CTE is a logical readability boundary, not a promise that SQLite must materialize it. The recorded plan is actual evidence for the current datasets; no PostgreSQL/MySQL execution is claimed.

## Optimization and common mistakes

Keep source and format filtering before aggregation. Avoid joining memberships or match appearances, which would multiply career rows. Do not use COUNT(runs) as participation evidence: known zero runs can still represent a played format, and unknown runs can coexist with known matches_played. Do not average rounded reported averages or divide by matches/batting innings.

SUM normally ignores NULLs, so the explicit COUNT(*) = COUNT(column) checks are necessary to avoid presenting an incomplete pooled average as complete for the included rows. NULLIF prevents dividing by zero. Group by identity rather than name alone. HAVING applies the format-count criterion after groups exist; WHERE cannot apply that aggregate condition.

COUNT(DISTINCT code) communicates the eligibility rule clearly even though latest-view uniqueness and one selected source already prevent multiple rows per player/format. It incurs a small aggregation cost in the observed plan. No new index or schema change was justified; on substantially larger data, benchmark latest-snapshot selection and grouping before changing the query or introducing a maintained projection.

## Verification and checkpoint

The full suite passes **273 tests**; lint, formatting and whitespace checks pass. Six focused tests cover two-format qualification/pivoting; weighted versus simple-mean averages; zero/unknown appearance counts; all three formats; genuine zero runs; zero total dismissals; missing runs/dismissals preventing partial averages; ambiguous T20 exclusion; deleted players; source isolation/latest snapshots; and separate same-named people. Test modifications occur only in isolated temporary databases. Working databases were read without changes; no API request was used.

Question 11 is complete. Question 12 has not been implemented. Say **NEXT** to proceed to Question 12.
