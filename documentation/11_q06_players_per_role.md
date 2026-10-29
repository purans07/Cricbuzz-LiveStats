# Phase 11 — Question 6: player count per playing role

## Business problem

The exact brief asks: “Count how many players belong to each playing role (like Batsman, Bowler, All-rounder, Wicket-keeper). Show the role and count of players for each role.” This describes the role composition of the stored active player population.

## Concepts, tables and relationships before SQL

Use LEFT JOIN to keep every defined role, COUNT of the matched player ID to count people, GROUP BY to aggregate by role identity/name, and ORDER BY to make results stable and easy to read.

`playing_roles.role_id` identifies each role and its `name`. `players.role_id` optionally references a role. `v_active_players` exposes only profiles with is_deleted=0. Each profile has one current primary role; this schema does not classify a player into multiple roles at once.

## Query logic and execution strategy

Start from the role catalogue. Attach active players with the matching role ID, count their non-null player IDs, and group by role ID/name. Keep defined roles without active players as zero. Sort by largest player count first, then role name and ID for deterministic ties. The question does not require a particular ordering, so this is a presentation choice rather than an additional eligibility rule.

Unknown role is absence of classification, not evidence of any particular role. Players with role_id=NULL do not join a known role and are excluded from its counts. Inventory these separately so the total assigned population is not mistaken for all stored players. Do not infer “Bowler” from an observed bowling line or “Wicket-keeper” from a catch. Role labels come from the catalogue and are not silently merged as synonyms.

The expected small-table execution scans roles, looks up players by role and sorts aggregates. The actual plan is recorded below.

## SQL query

```sql
-- Q06: Count active players for every defined playing role.
SELECT
    r.name AS playing_role,
    COUNT(p.player_id) AS player_count
FROM playing_roles AS r
LEFT JOIN v_active_players AS p ON p.role_id = r.role_id
GROUP BY r.role_id, r.name
ORDER BY player_count DESC, r.name ASC, r.role_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment identifies Question 6 and limits counts to active players. |
| 2 | Begin selecting output columns. |
| 3 | Return the role's name as playing_role. |
| 4 | Count non-null matching player IDs and name the result player_count. |
| 5 | Begin with every defined role, using alias r. |
| 6 | Attach undeleted players whose role ID matches; retain a role even when no player matches. |
| 7 | Produce one aggregate row per role ID and name. |
| 8 | Sort highest count first, then alphabetically by role name and finally by ID; end the statement. |

## Why the join and count matter

COUNT(p.player_id) gives zero for an unmatched role because it ignores NULL. COUNT(*) would count the LEFT JOIN's unmatched row and incorrectly report one player. An inner join would omit zero-player roles entirely.

Count player identities, not distinct names: different players can have the same name. Do not join match_players, memberships or performance tables to this question; one player can appear in many matches and memberships, which would multiply rows and inflate counts. Deleted profiles are filtered inside v_active_players before the join. Putting a filter on player columns in the outer WHERE could accidentally remove roles with no active players.

## Running it and measured results

Load `sql/queries/q06_players_per_role.sql` and execute SQLAlchemy `text(query)` in an existing read transaction. No input parameter is required. The question uses the current stored profile role, not a historical role as of a match date. No nationality, team, format or match-appearance eligibility is specified.

The fictional sample returns:

| playing_role | player_count |
| --- | ---: |
| All-rounder | 3 |
| Batsman | 3 |
| Bowler | 3 |
| Wicket-keeper | 3 |

All 12 active sample players have known roles. The live catalogue currently contains Batsman and its count is one. Of 22 active live profiles, 21 have role_id=NULL. The one enriched profile is Temba Bavuma. These numbers describe limited enrichment, not the real-world distribution of cricket roles.

The catalogue differs between sample and live databases. A role never imported into the live catalogue cannot appear as a zero row; the query keeps every **defined** role, not a hardcoded list of four roles. It also counts source-scoped local player identities separately; cross-provider person deduplication is not claimed.

Complete outputs, unknown-role counts and plans are in `11_q06_result.json`. Working databases were only read; no API request was used.

## Actual execution plan and optimization

Both working databases report:

1. `SCAN r`: read the small role catalogue.
2. `SEARCH players USING INDEX idx_players_role (role_id=?) LEFT-JOIN`: expand the active-player view and find profiles for each role.
3. `USE TEMP B-TREE FOR ORDER BY`: sort the calculated counts.

The existing role index supplies the join lookup. The active-player condition still excludes deleted rows. The aggregate result is computed before sorting; an index on role name alone does not precompute count order.

No new index is justified by the four-role sample and 22-player live inventory. On a much larger dataset, measure role lookup plus deleted-row filtering before considering a composite role/deletion index. COUNT(DISTINCT name) would be incorrect for different people with equal names; COUNT(DISTINCT player_id) is unnecessary in this direct one-role-to-player join. SQLite's measured plan is not verification of PostgreSQL/MySQL execution.

## Verification and checkpoint

The full suite passes **246 tests**; lint, formatting and whitespace checks pass. Five focused tests cover sample counts/output order; a defined unused role returning zero; soft-deleted and unassigned profiles; different identities sharing names without match-appearance multiplication; and all roles returning zero when every player is deleted. Test changes occur only in isolated temporary copies.

Question 6 is complete. Question 7 has not been implemented. Say **NEXT** to proceed to Question 7.
