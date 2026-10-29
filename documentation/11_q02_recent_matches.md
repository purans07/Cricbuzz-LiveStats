# Phase 11 — Question 2: matches played in the last 30 days

## Business problem

The project brief asks: “Show all cricket matches that were played in the last 30 days. Include the match description, both team names, venue name with city, and the match date. Sort by most recent matches first.” This supplies a recent-match listing with enough context to identify each game.

## Definitions before implementation

Use a **rolling 30 × 24-hour window**, based on match start time. It is not “the previous calendar month” and not “completed in the last 30 days.” Both endpoints are inclusive: window_start <= starts_at <= as_of_utc. A long match that started before the window is excluded even if it continued within it. Unknown start times are excluded because their eligibility cannot be established.

For this lesson, completed status is accepted as evidence of a played match when innings coverage is absent. Ongoing or abandoned matches require an innings with legal_balls > 0. That excludes a live-list match still at the toss. Scheduled and unknown-status matches are excluded. This policy is explicit: completed no-play/no-result matches may need stricter filtering if later provider metadata distinguishes them; completed status alone does not prove a ball was bowled. The query does not interpret status prose or invent missing play evidence. A match with only illegal deliveries and zero legal balls would also lack enough evidence under this definition.

## SQL concepts, tables and relationships

Concepts: joins, table aliases, range conditions, IN, correlated EXISTS, optional relationships, and descending order with a stable tie-breaker.

- `matches` stores description, UTC start, status and optional venue ID.
- `match_teams` links each match to two teams through unique slots 1 and 2.
- `teams` supplies each name. Join this table twice using aliases t1 and t2.
- `venues` supplies name and city; LEFT JOIN preserves unknown venues.
- `innings` supplies optional positive-ball evidence without multiplying output rows.

The uniqueness of (match_id, slot) ensures at most one participant in each requested slot. A missing participant excludes the match through the inner joins rather than inventing a team name. A Test match with several innings still returns one row because the innings check uses EXISTS.

## Query logic and planned execution

First identify matches in the requested start-time/status scope. Resolve participant slot 1 and slot 2, then resolve each team name. Look up an optional venue. For unfinished or abandoned matches, check for evidence of play. Sort newest first. This is the logical explanation; the optimizer decides actual physical access order.

## SQL query

```sql
-- Q02: Matches started within a rolling 30-day UTC window.
-- Bind window_start and as_of_utc as canonical UTC timestamps.
SELECT
    m.description AS match_description,
    t1.name AS team1_name,
    t2.name AS team2_name,
    v.name AS venue_name,
    v.city AS venue_city,
    m.starts_at AS match_date
FROM matches AS m
JOIN match_teams AS mt1 ON mt1.match_id = m.match_id AND mt1.slot = 1
JOIN teams AS t1 ON t1.team_id = mt1.team_id
JOIN match_teams AS mt2 ON mt2.match_id = m.match_id AND mt2.slot = 2
JOIN teams AS t2 ON t2.team_id = mt2.team_id
LEFT JOIN venues AS v ON v.venue_id = m.venue_id
WHERE m.starts_at >= :window_start
  AND m.starts_at <= :as_of_utc
  AND m.status IN ('completed', 'live', 'abandoned')
  AND (
      m.status = 'completed'
      OR EXISTS (
          SELECT 1 FROM innings AS i
          WHERE i.match_id = m.match_id AND i.legal_balls > 0
      )
  )
ORDER BY m.starts_at DESC, m.match_id DESC;
```

## Every line explained

| SQL file line | Meaning |
| --- | --- |
| 1 | Comment identifies the question and start-time window. |
| 2 | Comment describes the two bound UTC parameters. |
| 3 | Begin the output column list. |
| 4 | Return the match description with a descriptive column alias. |
| 5 | Return the first team’s name. |
| 6 | Return the second team’s name. |
| 7 | Return the venue name, or NULL when unknown. |
| 8 | Return venue city, or NULL when unknown. |
| 9 | Return the stored start timestamp as match_date. It is UTC, not a local date conversion. |
| 10 | Read matches, with alias m. |
| 11 | Find the first participant slot for this match. |
| 12 | Look up that participant’s team name through its team ID. |
| 13 | Find the second participant slot for the same match. |
| 14 | Look up the second participant’s team name through its team ID. |
| 15 | Look up venue information when present, retaining matches with no venue. |
| 16 | Include the lower boundary of the rolling window. |
| 17 | Include the analysis timestamp but exclude starts after it. |
| 18 | Exclude scheduled and unknown-status matches. |
| 19 | Group the alternatives that establish play for this lesson. |
| 20 | Accept completed status even if detailed innings have not been imported. |
| 21 | Otherwise require at least one innings with recorded play. |
| 22 | EXISTS checks presence; it does not join every innings into the output. |
| 23 | Correlate innings to this match and require a positive legal-ball count. |
| 24 | Close the EXISTS subquery. |
| 25 | Close the grouped alternatives. |
| 26 | Sort newest start first; match ID descending breaks timestamp ties deterministically. |

## Bound parameters and running the query

For the reproducible sample, use as_of_utc = `2026-10-01T00:00:00Z` and window_start = `2026-09-01T00:00:00Z`. Calculate the start from the endpoint rather than independently entering two unrelated dates:

```python
from datetime import datetime, timedelta
from sqlalchemy import text
from utils.dates import normalize_timestamp

as_of = normalize_timestamp("2026-10-01T00:00:00Z")
start = datetime.fromisoformat(as_of.replace("Z", "+00:00")) - timedelta(days=30)
parameters = {
    "window_start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "as_of_utc": as_of,
}
# Within an existing database.transaction() read context:
# rows = connection.execute(text(query), parameters).mappings().all()
```

Load `query` from `sql/queries/q02_recent_matches.sql`. Bind values; never format input directly into SQL. All persisted timestamps must follow the established second-precision UTC format, so lexical comparisons preserve chronological order. Local display can use `utils.dates.display_timestamp` later; do not convert indexed timestamps in the WHERE clause. Venue name and city are separate output columns, preserving independent NULL values.

## Actual results and SQLite execution plan

`11_q02_result.json` records the complete outputs, exact parameters and real EXPLAIN QUERY PLAN results from read-only connections:

- Sample: **six fictional matches**, ending at the fixed sample timestamp, 1 October 2026 00:00 UTC. Most recent is Synthetic match 072 at 21 September 2026 08:00 UTC.
- Live: **four stored matches**, ending at the last Phase 9 acceptance timestamp, 22 October 2026 07:52:06 UTC. This is an intentionally reproducible historical snapshot, not an API refresh or a complete world-wide match list.

Observed physical plan on both working databases:

1. Search matches with `idx_matches_status_date` using status.
2. For the correlated innings check, search the existing innings uniqueness index by match_id.
3. Resolve each participant with the unique match_id/slot index.
4. Resolve team and venue names using integer primary keys.
5. Sort the final results using a temporary B-tree.

The optimizer chose the status prefix of the existing `(status, completed_at)` index. That index does **not** provide the starts_at range; the start-time predicates are still applied as filters. An existing `idx_matches_start` is available, but it was not selected in this observed plan. SQLite may choose differently with larger data or updated statistics. PostgreSQL/MySQL plans are not verified.

## Optimization

Compare starts_at directly to bound timestamps; wrapping it in date() can prevent a useful range access path. Join by integer IDs and constrain both participant slots to avoid the four combinations produced by joining unconstrained participants twice. EXISTS avoids an innings join that would duplicate Test-match rows. Keep venue optional with LEFT JOIN.

Do not add an index based only on a small demonstration. If larger representative data shows a bottleneck, benchmark the existing start-time access path against a possible `(status, starts_at)` index and inspect the resulting sort/IN behavior. A proposed index is not evidence of an improvement, and a status lookup is not evidence that the date condition is indexed. No schema change or optimizer hint was introduced for this lesson.

## Verification and checkpoint

The full suite passes **226 tests**; lint, formatting and whitespace checks pass. Four dedicated tests cover exact lower/upper boundaries, future exclusion, team-slot mapping, missing venue, status/play evidence, NULL dates, and multiple innings without duplicate output. Tests modify only temporary database copies. The working datasets were read without modification, and no API request was used.

Question 2 is complete. Question 3 has not been implemented. Say **NEXT** to proceed to Question 3.
