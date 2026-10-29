# Phase 11 — Question 9: qualifying career all-rounders

## Business problem

The exact brief asks: “Find all-rounder players who have scored more than 1000 runs AND taken more than 50 wickets in their career. Display player name, total runs, total wickets, and the cricket format.” This identifies players who meet both batting and bowling milestones within a format.

## Concepts, tables and relationships before SQL

Use joins to resolve player/role/format/source identities, WHERE for eligibility, strict greater-than comparisons, AND for simultaneous thresholds, and deterministic ORDER BY. GROUP BY and HAVING are unnecessary: the selected latest career rows already contain the totals at the required player/format/source grain.

`players.role_id` references `playing_roles.role_id`. `career_stats_snapshots.player_id` references the player; format_id references `formats`; batch_id references `import_batches`, whose source_id identifies `sources`. `v_latest_career` selects the latest committed snapshot per player/format/source by fetch time and batch-ID tie-breaker, excludes deleted profiles, and ignores pending/failed batches.

## Logic and execution strategy

Select one source, then require the canonical All-rounder role. For each latest career row, test runs > 1000 AND wickets > 50. A player may appear once in each qualifying format. Do not combine Test runs with ODI wickets or add successive snapshots together.

Unknown runs or wickets do not satisfy the threshold. Zero remains a known nonqualifying value. Requiring both known totals avoids converting incomplete data into an apparent all-round achievement. Exactly 1000 runs or exactly 50 wickets fails the question's strict wording.

This uses the stored current primary role, not a historical role as of a match date. Strong statistics alone do not establish a profile classification. Only the canonical role label All-rounder is selected. Unknown roles and other free-text labels are not silently mapped; any new provider labels such as specialized batting/bowling all-rounder labels need an evidence-based role mapping before being treated as equivalent.

The question does not restrict formats to Test/ODI/T20I, so the query returns each eligible stored career format code as-is. It does not promote INTERNATIONAL_T20 to T20I or combine domestic and international totals. Snapshot import must already align career batting/bowling scopes; this query cannot reconstruct inconsistent source requests.

Logically: find all-rounder profiles and the selected source, resolve latest career rows and format, apply both thresholds, and order the eligible rows. Physical join order is the optimizer's decision, measured below.

## SQL query

```sql
-- Q09: All-rounders exceeding both career thresholds within the same format.
-- Bind source_name; each output row represents one player and format.
SELECT
    p.full_name AS player_name,
    c.runs AS total_runs,
    c.wickets AS total_wickets,
    f.code AS cricket_format
FROM v_latest_career AS c
JOIN players AS p ON p.player_id = c.player_id
JOIN playing_roles AS r ON r.role_id = p.role_id
JOIN formats AS f ON f.format_id = c.format_id
JOIN sources AS s ON s.source_id = c.source_id
WHERE r.name = 'All-rounder'
  AND s.name = :source_name
  AND c.scope = 'career'
  AND c.runs > 1000
  AND c.wickets > 50
ORDER BY c.runs DESC, c.wickets DESC, p.player_id ASC, f.code ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment specifies that both thresholds must be exceeded within the same format. |
| 2 | Comment specifies the bound source and one-player/one-format output grain. |
| 3 | Begin selecting output columns. |
| 4 | Return the player name. |
| 5 | Return career runs, not a sum of our imported scorecards. |
| 6 | Return career wickets from that same snapshot. |
| 7 | Return the exact stored format code. |
| 8 | Read the latest committed career snapshot view, which excludes deleted profiles. |
| 9 | Resolve the player identity and current profile name. |
| 10 | Resolve the current primary playing-role label. |
| 11 | Resolve the cricket format. |
| 12 | Resolve the snapshot source through its source ID. |
| 13 | Require the evidenced canonical All-rounder role. |
| 14 | Keep only the source supplied as a bound parameter. |
| 15 | Explicitly require career rather than series scope. |
| 16 | Require more than 1,000 runs; exactly 1,000 does not qualify. |
| 17 | Also require more than 50 wickets; exactly 50 does not qualify. |
| 18 | Sort runs descending, then wickets descending; player ID and format code give stable ties. |

## Running the query and actual results

Load `sql/queries/q09_qualified_all_rounders.sql` and execute SQLAlchemy `text(query)` in an existing read transaction, binding source_name to `Synthetic training fixture` for sample data or `cricketapilive-cricbuzz-cricket/v2/provider` for live data. Do not concatenate the source name into SQL. A missing source returns no rows.

The fictional sample has nine qualifying rows:

| Player | Runs in each listed format | Wickets in each listed format | Qualifying formats |
| --- | ---: | ---: | --- |
| Sample Player 11 | 2860 | 93 | ODI, T20I, TEST |
| Sample Player 07 | 2380 | 81 | ODI, T20I, TEST |
| Sample Player 03 | 1900 | 69 | ODI, T20I, TEST |

This table summarizes the query's separate per-format rows; its runs/wickets are not summed across formats. The repeated sample totals are synthetic simplifications, not professional cricket records.

Live data returns no qualifying rows. Only one profile/career has been enriched, and that profile is classified Batsman. Twenty-one other active profiles lack role evidence. Empty output therefore does not establish that no real-world all-rounders meet the thresholds. Wider profile/career coverage remains required.

The view supplies latest stored snapshots, not a historical as-of ranking or a guarantee of synchronized fetch times for every player. Source-scoped identities remain separate; identical player names are not deduplicated. Full outputs and plans are in `11_q09_result.json`. Working databases were read without changes, and no API request was used.

## Actual SQLite execution plan

Both databases used the unique role-name and source-name indexes to resolve All-rounder and the selected source, then `idx_players_role` to find candidate profiles. SQLite looked up active player rows, career snapshots by the player/format/batch uniqueness index, batches by primary key, and formats by primary key.

The latest-snapshot anti-existence checks used source/fetch-time and snapshot-identity indexes to test newer committed candidates. A temporary B-tree sorted final qualifying rows. These are the actual observed SQLite access paths, not a claim about PostgreSQL/MySQL or large-dataset performance.

## Optimization

Do not join innings, appearances or match performances: their one-to-many rows can multiply data and do not supply complete career totals. Avoid SUM and HAVING on already aggregated career snapshots. Filtering on the role ID after a unique role-name lookup uses the existing role index. Keep numeric comparisons directly on runs/wickets, without converting numbers to strings or replacing NULL with zero.

AND is essential; OR would admit a specialist meeting only one milestone. DISTINCT is unnecessary because the view already supplies one eligible latest record per identity/format/source. No top-N limit is applied: the brief asks for all qualifying players.

No new index or schema change was introduced. On substantially larger data, measure role selectivity and latest-snapshot selection before considering a composite index or maintained current-career projection. A numeric-threshold index on historical snapshots alone cannot establish which rows are latest, and indexes have storage/write costs.

## Verification and checkpoint

The full suite passes **261 tests**; lint, formatting and whitespace checks pass. Five focused tests cover strict threshold boundaries and AND; no cross-format combination; one output row per eligible format; explicit role/deleted/NULL handling; latest snapshots rather than larger old totals; source isolation and bound hostile-looking input; and separate same-named identities with ordered run/wicket ties. All test modifications occur in temporary databases.

Question 9 is complete. Question 10 has not been implemented. Say **NEXT** to proceed to Question 10.
