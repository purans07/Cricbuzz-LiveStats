# Phase 11 — Question 20: career match counts and averages by format

## Business problem

The exact brief asks: “Analyze how many matches each player has played in different cricket formats and their batting average in each format. Show the count of Test matches, ODI matches, and T20 matches for each player, along with their respective batting averages. Only include players who have played at least 20 total matches across all formats.”

## Scope and statistical definitions before SQL

Use the latest committed **career** snapshots from one selected source, not the number of scorecards imported into our local database. The displayed categories and threshold scope are the three requested international career buckets: Test, ODI and T20. IPL/domestic totals are not added to those international totals. This is an explicit interpretation of “all formats” as the requested target categories, not every league a player has ever represented.

Test maps only code TEST; ODI maps only code ODI. T20 accepts one international-level source bucket among T20, T20I and INTERNATIONAL_T20. Unlike Questions 7/11, this brief asks for T20 rather than verified T20I. The ambiguous provider INTERNATIONAL_T20 bucket may therefore be displayed under its broader T20 label without asserting official T20I eligibility.

Do not add multiple T20 candidates for the same player/source: they may overlap. Reject an ambiguous player comparison rather than choosing the largest bucket or double-counting. Each latest career code must map to one distinct output category for that player.

Require at least twenty known matches across the represented target categories. Any represented row with unknown count prevents an exact sum for those rows and excludes that comparison. Missing categories stay NULL, not fabricated zero. If known represented categories already total twenty, the player can qualify while an absent category remains unknown; total_known_matches labels the available evidence, not a guarantee of globally complete career representation. An explicitly known zero count stays zero.

Batting average uses career runs / dismissals when dismissals are positive, with real arithmetic. When the dismissal denominator is unknown, use the separately stored provider-reported average if supplied. Zero dismissals leave average undefined. Unknown runs with a known positive denominator remain NULL rather than silently replacing a calculation with a different evidence source. Match appearances are not the batting-average denominator.

## Concepts, tables and relationships

Use a CTE, CASE category mapping, conditional aggregation MAX(CASE...), source/format joins, GROUP BY, COUNT completeness/uniqueness guards, SUM and HAVING, and ROUND only for displayed averages.

`v_latest_career` supplies the latest committed player/format/source row by fetch timestamp and batch-ID tie-breaker, excluding deleted players and failed/pending batches. `players` supplies name/identity, `formats` supplies exact code and level, and `sources` supplies the selected origin. No playing-role restriction is requested.

## Query logic and execution strategy before SQL

Select one source and the target international formats, map each to a display category and calculate the format-specific average. Group by player. Before accepting the result, require exactly one row per mapped category and known counts, then apply SUM(matches)>=20.

MAX(CASE...) extracts the only permitted category's count/average; it does not pick a best historical snapshot. Latest snapshot selection already occurred. No ELSE 0 means an absent category stays NULL. The uniqueness guard prevents MAX from silently choosing one overlapping T20 bucket. Do not SUM career snapshots across fetch dates or average already-reported averages together.

The expected logical stages are source/format selection, latest-row eligibility, category mapping, per-player pivot, total/ambiguity checks and name ordering. The measured physical plan appears below.

## SQL query

```sql
-- Q20: Latest selected-source international format careers, >=20 known matches.
WITH format_careers AS (
    SELECT p.player_id, p.full_name,
        CASE WHEN f.code = 'TEST' THEN 'Test'
             WHEN f.code = 'ODI' THEN 'ODI'
             ELSE 'T20' END AS format_group,
        c.matches_played,
        CASE WHEN c.dismissals > 0 THEN 1.0 * c.runs / c.dismissals
             WHEN c.dismissals IS NULL THEN c.reported_batting_average
        END AS batting_average
    FROM v_latest_career AS c
    JOIN players AS p ON p.player_id = c.player_id
    JOIN formats AS f ON f.format_id = c.format_id
    JOIN sources AS s ON s.source_id = c.source_id
    WHERE s.name = :source_name
      AND c.scope = 'career'
      AND f.level = 'international'
      AND f.code IN ('TEST', 'ODI', 'T20', 'T20I', 'INTERNATIONAL_T20')
)
SELECT
    full_name AS player_name,
    MAX(CASE WHEN format_group = 'Test' THEN matches_played END) AS test_matches,
    ROUND(MAX(CASE WHEN format_group = 'Test' THEN batting_average END), 2)
        AS test_batting_average,
    MAX(CASE WHEN format_group = 'ODI' THEN matches_played END) AS odi_matches,
    ROUND(MAX(CASE WHEN format_group = 'ODI' THEN batting_average END), 2)
        AS odi_batting_average,
    MAX(CASE WHEN format_group = 'T20' THEN matches_played END) AS t20_matches,
    ROUND(MAX(CASE WHEN format_group = 'T20' THEN batting_average END), 2)
        AS t20_batting_average,
    SUM(matches_played) AS total_known_matches
FROM format_careers
GROUP BY player_id, full_name
HAVING COUNT(*) = COUNT(DISTINCT format_group)
   AND COUNT(*) = COUNT(matches_played)
   AND SUM(matches_played) >= 20
ORDER BY full_name ASC, player_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states the latest single-source international-career scope and known-match threshold. |
| 2 | Create a CTE for format-level careers with consistent output categories. |
| 3 | Keep player identity and name. |
| 4 | Map the exact TEST code to the Test display category. |
| 5 | Map the exact ODI code to ODI. |
| 6 | Map accepted international T20 codes to the T20 display category, without claiming T20I equivalence. |
| 7 | Keep provider career match count. |
| 8 | Calculate a batting average from known runs and positive dismissals. |
| 9 | If dismissals are unknown, allow the separately stored reported average as a fallback. |
| 10 | Name the nullable unrounded format average; zero dismissals produce NULL. |
| 11 | Read latest committed career snapshots, excluding deleted profiles. |
| 12 | Resolve the profile name/identity. |
| 13 | Resolve format classification. |
| 14 | Resolve the snapshot source. |
| 15 | Keep only the source supplied as a bound value. |
| 16 | Require career scope, not a series aggregate. |
| 17 | Restrict this comparison to international-level buckets. |
| 18 | Accept only exact Test, ODI and supported international T20 candidate codes. |
| 19 | End the CTE. |
| 20 | Begin the per-player pivot. |
| 21 | Return player name. |
| 22 | Extract the Test match count from the grouped format rows. |
| 23 | Extract and round the Test batting average. |
| 24 | Name the Test average column. |
| 25 | Extract the ODI match count. |
| 26 | Extract and round the ODI average. |
| 27 | Name the ODI average column. |
| 28 | Extract the single accepted T20 match count. |
| 29 | Extract and round the T20 average. |
| 30 | Name the T20 average column. |
| 31 | Sum the unambiguous known counts for the selected target categories. |
| 32 | Read the mapped format career rows. |
| 33 | Group by player identity/name, not name alone. |
| 34 | Require one row per output format category; reject overlapping T20 candidate rows. |
| 35 | Require known match counts in all represented target rows. |
| 36 | Require at least twenty known matches; exactly twenty qualifies. |
| 37 | Sort by player name, then identity for stable same-name ties. |

## Running it and measured results

Load `sql/queries/q20_format_matches_and_averages.sql` and execute SQLAlchemy `text(query)` inside an existing read transaction. Bind source_name to `Synthetic training fixture` for sample data or `cricketapilive-cricbuzz-cricket/v2/provider` for live data. Missing/hostile-looking source values do not become SQL code and yield no qualifying rows.

The fictional sample returns 12 players. Sample Player 01 has 43 known matches in each of its three synthetic formats, 129 in total, with batting averages 40.49 in each. These repeated totals are seed simplifications, not factual professional records.

Live data returns one enriched career profile:

| Player | Test matches / average | ODI matches / average | T20 matches / average | Total known |
| --- | --- | --- | --- | ---: |
| Temba Bavuma | 68 / 38.77 | 57 / 43.36 | 36 / 20.94 | 161 |

The source's T20 code is INTERNATIONAL_T20; this is not a claim of independently verified T20I classification. The live result contains one player's career because only one profile has been enriched, not because only one real player meets the threshold. Career counts can exceed local imported match coverage by design.

No historical as-of date or synchronized player-fetch guarantee is added. Source-scoped identities remain separate even for equal names. Full outputs, actual T20 codes and plans are in `11_q20_result.json`. Working databases were read without changes; no API request was made.

## Actual SQLite execution plan and optimization

Both datasets resolve source name and format codes with their unique indexes, access career candidates through `idx_career_format_player`, and use primary-key batch/player lookups. The latest-row anti-existence logic uses the source/fetch-time and player/format/batch uniqueness indexes. Temporary B-trees support grouping, COUNT(DISTINCT) and final ordering.

Keep source and exact format filters before aggregation. Do not join match appearances or performance rows to career totals: local history is incomplete and such joins can multiply counts. Group by identity instead of name. Use SUM for disjoint format match counts and separate dismissal-based averages; averaging averages across formats would change the question.

The COUNT(DISTINCT format_group) comparison is a semantic safety check, not gratuitous duplicate removal. Unknown represented counts are deliberately rejected rather than ignored by SUM. No new index or schema change was justified; on a larger dataset, benchmark latest-snapshot selection and grouping before considering a maintained projection. SQLite plans are not PostgreSQL/MySQL execution verification.

## Verification and checkpoint

The full suite passes **329 tests**; lint, formatting and whitespace checks pass. Seven focused tests cover the exact 19/20-match boundary; latest snapshots and source isolation; unknown versus known-zero counts; missing/domestic T20 not fabricated into a target bucket; zero dismissals and reported-average fallback; overlapping T20 buckets rejected; deleted profiles; and equal-named people kept separate. Test writes occur only in isolated temporary databases.

Question 20 is complete. Question 21 has not been implemented. Say **NEXT** to proceed to Question 21.
