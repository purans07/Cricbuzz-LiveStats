# Phase 11 — Question 1: players representing India

## Business problem

The exact brief asks: “Find all players who represent India. Display their full name, playing role, batting style, and bowling style.” This supports finding player profiles for an international side.

Our schema stores representation through evidenced, dated team memberships rather than a `country` column on the player. As agreed in database design, interpret representation **as of a chosen analysis date**. Membership start and end dates are inclusive. An Indian domestic club is not evidence of international representation. Nationality and birthplace are not substituted for representation.

## Concepts, tables and relationships

Use `SELECT` for the four requested columns, `LEFT JOIN` for optional role information, `EXISTS` to check eligibility without multiplying profile rows, and `ORDER BY` for stable output. `IS NULL` handles open-ended memberships explicitly.

`v_active_players` exposes undeleted `players` records. `players.role_id` references `playing_roles.role_id`. `player_team_memberships.player_id` references the player; its `team_id` references `teams.team_id`. `teams.country_id` references `countries.country_id`. `teams.is_international` distinguishes representative teams from domestic clubs. These relationships are already indexed and enforced by foreign keys.

## Logic and execution strategy before the query

Start with active player identities. For each player, check whether at least one membership is valid on the analysis date and leads to an international team associated with India. Keep that player once, join a role if known, and sort by full name with player ID as a tie-breaker. Do not use name equality to identify people or DISTINCT to collapse identical-looking profiles.

The logical explanation does not force the optimizer's physical join order. After execution, inspect SQLite's actual plan, recorded below.

## SQL

```sql
-- Q01: Players representing India on the bound analysis date.
-- The as_of_date parameter uses YYYY-MM-DD; membership end dates are inclusive.
SELECT
    p.full_name,
    r.name AS playing_role,
    p.batting_style,
    p.bowling_style
FROM v_active_players AS p
LEFT JOIN playing_roles AS r ON r.role_id = p.role_id
WHERE EXISTS (
    SELECT 1
    FROM player_team_memberships AS pm
    JOIN teams AS t ON t.team_id = pm.team_id
    JOIN countries AS c ON c.country_id = t.country_id
    WHERE pm.player_id = p.player_id
      AND t.is_international = 1
      AND c.name = 'India'
      AND pm.valid_from <= :as_of_date
      AND (pm.valid_to IS NULL OR pm.valid_to >= :as_of_date)
)
ORDER BY p.full_name, p.player_id;
```

## Every SQL line explained

Line numbers below refer to `sql/queries/q01_india_players.sql`.

| Line | Meaning |
| --- | --- |
| 1 | Comment identifies Question 1 and its date-based definition. |
| 2 | Comment specifies ISO dates and inclusive membership ends. Avoid writing a colon-prefixed bind token in a SQLAlchemy SQL comment: SQLAlchemy can parse it as an extra bind parameter. |
| 3 | `SELECT` begins the requested output projection. |
| 4 | Return the player's full name. |
| 5 | Return the role name, labeling the output column `playing_role`. |
| 6 | Return batting style, including NULL when unknown. |
| 7 | Return bowling style, including NULL when unknown. |
| 8 | Read the active-player view; deleted profiles are excluded. `p` is its alias. |
| 9 | Match the role ID to its name; LEFT JOIN retains players with no role. |
| 10 | Keep a player if the following subquery finds at least one qualifying membership. |
| 11 | The literal 1 is conventional: EXISTS checks presence, not the returned value. |
| 12 | Read membership records, aliased `pm`. |
| 13 | Follow the membership's team ID to that team, aliased `t`. |
| 14 | Follow the team's country ID to its country, aliased `c`. |
| 15 | Correlate the membership with the current outer player ID. |
| 16 | Require an international representative team. |
| 17 | Require its country name to be India. |
| 18 | Membership must have started by the bound analysis date. |
| 19 | Its end must be unknown/open-ended or on/after that date. |
| 20 | End the EXISTS check. Multiple matches still keep one outer profile. |
| 21 | Sort by name, then player ID; terminate the statement. |

## Running it safely

Load the SQL file and execute with SQLAlchemy `text(query)` and `{"as_of_date": "2026-10-01"}` as bound parameters. Do not concatenate a user-entered date into SQL. The date should be validated with `utils.dates.validate_date` when a user-facing runner is built. The sample's fixed analysis date is 1 October 2026; use an explicit chosen date rather than relying on the computer's current date.

The existing `stored_query` repository helper remains limited to operational queries. This lesson does not expand arbitrary SQL access or create the later analytics interface.

## Observed results and execution plan

The unchanged working sample returns **six fictional profiles**, Sample Player 01 through Sample Player 06. These are synthetic training records, not a factual India squad. Full results and query plans are saved in `11_q01_result.json`.

The live database returns zero rows because its `player_team_memberships` table has zero rows. It contains scorecard identities but no dated international representation evidence. Empty output is a coverage limitation, not proof of no qualifying real-world players. This lesson makes no API request and does not fabricate memberships.

Observed SQLite plan on the working sample:

1. Scan `players` (the active view is expanded into its base table).
2. Evaluate a correlated subquery for membership eligibility.
3. Search country using the unique country-name index.
4. Search memberships using `idx_memberships_player_dates (player_id, valid_from)`.
5. Look up teams and roles through their integer primary keys.
6. Use a temporary B-tree for the final requested ordering.

This is the measured plan for the small SQLite dataset, not a PostgreSQL/MySQL verification or a universal optimizer guarantee.

## Optimization

The existing membership index supports the correlated player equality and membership-start date range. Primary keys support team/role lookups, and the unique country-name index supports the India filter. EXISTS prevents duplicate output without a global DISTINCT sort and can stop once a qualifying membership is found. The role stays optional rather than being accidentally removed by an inner join. Keep dates as comparable ISO YYYY-MM-DD text; do not wrap indexed date columns in conversion functions unnecessarily.

The final sort is expected because no existing index supplies the requested name order after filtering. No extra index is added for 12 sample players. On a genuinely large dataset, measure again with EXPLAIN and representative workloads before adding a name-order index or comparing a country-driven semi-join. Do not assert faster execution solely because a query has more joins or indexes.

## Verification and checkpoint

The full suite passes **222 tests**; lint and formatting checks pass. Four dedicated Question 1 tests pass: expected sample results; date boundaries/unknown roles/deleted profiles; domestic-club exclusion; and duplicate memberships without collapsing two distinct people who share a name. All mutations in tests occur only in temporary database copies. Working databases were read without modification.

Question 1 is complete. Question 2 has not been implemented. Say **NEXT** to proceed to Question 2, as required by the adopted mentoring prompt.
