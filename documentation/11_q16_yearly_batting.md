# Phase 11 — Question 16: yearly batting trends since 2020

## Business problem

The exact brief asks: “Track how players' batting performance changes over different years. For matches since 2020, show each player's average runs per match and average strike rate for each year. Only include players who played at least 5 matches in that year.” This supplies yearly comparison rows suitable for a later trend chart; this lesson implements the data query, not that later dashboard/chart.

## Definitions and evidence before SQL

Year means the UTC calendar year of the match start time, beginning inclusively at 2020-01-01T00:00:00Z. A match spanning New Year belongs to its start year. Unknown dates cannot establish yearly eligibility. This is not a year-of-completion report or a local-timezone calendar.

At least five **match appearances** are needed in that year. Start from active match-player evidence, not only batting lines. Confirmed-XI and observed participation qualify in a completed match; live/abandoned matches additionally need positive-ball evidence that play began. A substitute-only label without ordinary batting evidence is excluded by this lesson's explicit participation policy. A replacement that played but lacks those evidence labels needs its participation classification enriched upstream; this query does not manufacture official caps. Completed status is accepted as play evidence when innings are unavailable, so no-play/no-result metadata can require later refinement.

This appearance policy is more inclusive than Question 15's explicitly “when they batted” population. If a qualifying player has no batting row, retain the appearance and leave its batting totals unknown. Absence cannot distinguish did-not-bat from incomplete ingestion. Do not assume a zero that the current schema has not explicitly established. A caller who requires known did-not-bat zeros will need stronger batting-participation evidence before filling them.

Average runs per match is the arithmetic mean of each appearance's combined ordinary-innings runs. A Test match with two innings counts once and sums those innings. If any included runs are unknown, the year's mean is NULL.

Average strike rate means the arithmetic mean of defined **per-match** strike rates, computed from combined match runs and balls faced. It is not the mean of innings strike rates or the pooled year's runs/balls ratio. Known zero-ball matches have undefined strike rate and do not contribute to AVG, while still contributing to match eligibility and known runs averages. If any appearance has unknown runs or balls, the annual strike-rate mean is NULL rather than silently using only complete matches. When all denominators are zero the mean is NULL.

## Concepts, tables and relationships

Use two CTEs; SUM for match totals; CASE/COUNT for completeness; LEFT JOIN for missing batting; EXISTS for play evidence; SUBSTR/CAST for UTC year extraction; GROUP BY/HAVING for yearly minimum appearances; AVG and NULLIF for correctly scoped means.

`v_active_batting` supplies undeleted ordinary-innings batting. `v_active_match_players` supplies undeleted-player match associations, unique at match/player grain. `matches` supplies starts/status, `innings` supplies optional evidence of play, and `players` supplies display names. Active batting aggregates are unique per player/match, so joining both keys preserves one appearance row.

No profile-role restriction is added: any recorded player can have batting figures. No format restriction is in the brief. These are all stored formats combined, not format-normalized or adjusted performance measures. Source-scoped local identities remain separate rather than being merged by names across providers.

## Logic and execution strategy before SQL

First combine active batting innings by player/match with completeness checks. Next attach those totals to eligible dated match appearances, deriving year from UTC start. Finally group by player/year, require five appearances, and compute the two means using their documented denominator policies. Return matches_played alongside requested averages so the minimum sample size is visible.

The optimizer may materialize the batting CTE and use a temporary lookup for the LEFT JOIN; the observed plan is recorded after the query.

## SQL query

```sql
-- Q16: Yearly match-based batting averages since 2020 (SQLite UTC years).
WITH match_batting AS (
    SELECT b.player_id, b.match_id,
        CASE WHEN COUNT(*) = COUNT(b.runs)
             THEN SUM(b.runs) END AS match_runs,
        CASE WHEN COUNT(*) = COUNT(b.balls_faced)
             THEN SUM(b.balls_faced) END AS match_balls
    FROM v_active_batting AS b
    GROUP BY b.player_id, b.match_id
), yearly_appearances AS (
    SELECT mp.player_id, m.match_id,
        CAST(SUBSTR(m.starts_at, 1, 4) AS INTEGER) AS match_year,
        mb.match_runs, mb.match_balls
    FROM v_active_match_players AS mp
    JOIN matches AS m ON m.match_id = mp.match_id
    LEFT JOIN match_batting AS mb
        ON mb.player_id = mp.player_id AND mb.match_id = mp.match_id
    WHERE m.starts_at >= '2020-01-01T00:00:00Z'
      AND m.status IN ('completed', 'live', 'abandoned')
      AND (m.status = 'completed' OR EXISTS (
          SELECT 1 FROM innings AS i
          WHERE i.match_id = m.match_id AND i.legal_balls > 0
      ))
      AND (mp.participation IN ('confirmed_xi', 'observed')
           OR mb.player_id IS NOT NULL)
)
SELECT p.full_name AS player_name, y.match_year,
    COUNT(*) AS matches_played,
    CASE WHEN COUNT(*) = COUNT(y.match_runs)
         THEN ROUND(AVG(y.match_runs), 2)
    END AS average_runs_per_match,
    CASE WHEN COUNT(*) = COUNT(y.match_runs)
              AND COUNT(*) = COUNT(y.match_balls)
         THEN ROUND(AVG(100.0 * y.match_runs / NULLIF(y.match_balls, 0)), 2)
    END AS average_strike_rate
FROM yearly_appearances AS y
JOIN players AS p ON p.player_id = y.player_id
GROUP BY p.player_id, p.full_name, y.match_year
HAVING COUNT(*) >= 5
ORDER BY p.full_name ASC, p.player_id ASC, y.match_year ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment identifies yearly match-based averages from 2020 and the SQLite UTC-year convention. |
| 2 | Define a CTE that aggregates ordinary batting innings per player/match. |
| 3 | Keep player and match identity. |
| 4 | Check whether every included innings has known runs. |
| 5 | Sum runs only when complete, naming the match run total. |
| 6 | Check whether every included innings has known balls faced. |
| 7 | Sum balls faced only when complete, naming the match ball total. |
| 8 | Read active batting rows, excluding deleted profiles/performances and super overs. |
| 9 | Produce one batting-total row per player/match. |
| 10 | Begin the second CTE for eligible yearly match appearances. |
| 11 | Keep player and match identity. |
| 12 | Extract the four-digit year from canonical UTC start time and convert it to an integer. |
| 13 | Attach nullable match batting totals. |
| 14 | Read active match-player associations. |
| 15 | Resolve match status and start time. |
| 16 | Optionally join match batting totals, retaining a valid appearance with missing batting data. |
| 17 | Match both player and match keys to avoid combining unrelated totals. |
| 18 | Include starts from 1 January 2020 UTC onward; unknown starts cannot pass. |
| 19 | Exclude scheduled/unknown-status fixtures. |
| 20 | Accept completed status, otherwise require evidence of play. |
| 21 | Check for an innings record. |
| 22 | Require that innings to belong to this match with positive legal balls. |
| 23 | Close the play-evidence condition. |
| 24 | Accept confirmed-XI/observed participation evidence. |
| 25 | Also accept a substitute-labelled player with active ordinary batting evidence. |
| 26 | End the appearance CTE. |
| 27 | Return player name and the UTC start year. |
| 28 | Count distinct-by-construction player-match appearance rows. |
| 29 | Only calculate runs average when every eligible appearance has known batting runs. |
| 30 | Average the match run totals and round once. |
| 31 | Name the per-match average. |
| 32 | Begin the strike-rate completeness condition. |
| 33 | Also require known balls faced for every eligible appearance. |
| 34 | Average per-match runs per 100 balls, excluding defined zero-ball denominators with NULLIF, then round once. |
| 35 | Name the average strike rate. |
| 36 | Read the eligible match appearances. |
| 37 | Resolve player name. |
| 38 | Group by player identity/name and start year. |
| 39 | Require at least five eligible match appearances within that year. |
| 40 | Sort by player name/identity, then ascending year for a time-series-friendly result. |

## Running it and observed results

Load `sql/queries/q16_yearly_batting.sql` and execute SQLAlchemy `text(query)` inside an existing read transaction. There are no parameters: the 2020 lower bound is fixed by the brief. No upper analysis-time cutoff is added; eligibility follows stored dated/played evidence.

The fictional sample returns **48 player-year rows**. Sample Player 01 illustrates the output:

| Year | Match appearances | Average runs per match | Mean match strike rate |
| --- | ---: | ---: | ---: |
| 2023 | 6 | 73.00 | 138.61 |
| 2024 | 24 | 90.50 | 140.91 |
| 2025 | 24 | 87.00 | 142.32 |
| 2026 | 18 | 96.33 | 143.95 |

These are simplified fictional performances, not factual professional trends. The live result is empty because only one match has imported player participation; nobody meets five in one year. Neither an empty result nor sample trends establish anything about real-world player form.

Full outputs, participation coverage and actual plans are in `11_q16_result.json`. Working databases were read without modifications, and no API call was used.

## Actual SQLite plan and optimization

Both working databases materialize match_batting, scanning active batting through the player/match index with primary-key player/innings checks. Match candidates use the status index in the observed plan; the start-time predicate is still applied, but the plan does not establish a start-date indexed range. The match-innings uniqueness index supports play-evidence lookups, and match-player indexes support appearance resolution.

SQLite uses a bloom filter and automatic covering index on the materialized player/match totals to support the LEFT JOIN. Temporary B-trees support the final player-year grouping and ordering. Those automatic structures are observed optimizer choices, not permanent schema additions or guarantees on another SQLite version. PostgreSQL/MySQL execution is not verified; year extraction syntax needs dialect review.

Keep the >=2020 predicate directly on canonical starts_at, rather than filtering solely with a year-extraction function. Extract the year only for grouping. Aggregate innings before joining appearances so a multi-innings match does not inflate eligibility or average weights. Avoid COUNT(DISTINCT name) or grouping by name alone; distinct people can share names.

Do not use batting rows alone as the five-match denominator unless deliberately changing the question to matches batted. Do not equate missing rows to zero or take AVG over incomplete totals without the explicit guard. Avoid rounding individual match strike rates before averaging. No new index or schema change was introduced; benchmark larger participation history before adopting a maintained per-match projection.

## Verification and checkpoint

The full suite passes **303 tests**; lint, formatting and whitespace checks pass. Six focused tests cover the exact 2020 boundary/NULL dates; five matches within one year rather than across years; multi-innings match totals and arithmetic mean strike rate; missing batting evidence, unknown balls and known zero denominators; substitute-only evidence; and deleted profiles/performances plus super overs. Test mutations occur only in isolated temporary databases.

Question 16 is complete. Question 17 has not been implemented. Say **NEXT** to proceed to Question 17.
