# Phase 11 — Question 12: home versus away wins

## Business problem

The exact brief asks: “Analyze each international team's performance when playing at home versus playing away. Determine whether each team played at home or away based on whether the venue country matches the team's country. Count wins for each team in both home and away conditions.” This summarizes confirmed winning outcomes by geographic condition.

## Definitions before SQL

Home means a known venue.country_id equal to team.country_id. Away means both are known and unequal. Under this exact rule, a neutral-country venue counts as away; this question does not distinguish neutral from an opponent's home venue.

A missing venue, missing venue country or missing team country is insufficient evidence for either condition. Eligible wins with those gaps are counted separately as unclassified_wins. This extra coverage column prevents unknown geography from silently becoming away. It counts only real eligible winning matches; a winless team with unknown country must still show zero unclassified wins.

Use stored teams.is_international=1 as the eligibility flag. The provider-derived flag currently reflects its international bucket and is not independent verification that every side, such as a warm-up XI, is an official national team. Team classification and country enrichment remain input-data requirements. Countries are compared by stable IDs, not names, substrings, venue city or series title.

## Concepts, tables and relationships

Use conditional aggregation SUM(CASE...), LEFT JOIN, equality/inequality, explicit NULL tests, WHERE for team eligibility, and GROUP BY for one row per team identity.

`teams` stores name, country_id and international flag. `matches.winner_team_id` references a participating team; status/result_type distinguish completed wins. `matches.venue_id` references `venues`, whose country_id identifies the location's country. Both country IDs reference countries, so this comparison does not need to join country names. Country names are not requested output fields.

## Query logic and planned execution

Start with international teams, then attach only completed matches with result_type='win' whose winner is that team. Resolve an optional venue, classify each real win using country identities, sum home/away/unclassified flags, and order by team name.

Do not count match appearances, toss wins, innings wins or draws. Joining the winner directly counts each winning match once. A win on a super-over decision can count even without a conventional run/wicket margin because the typed final result and winner determine eligibility.

For teams with no wins, LEFT JOIN supplies one NULL match row. Each CASE contributes zero for that row, preserving zero-win teams. The unclassified branch explicitly checks match_id IS NOT NULL; without it, missing geography on the unmatched row could incorrectly produce one unclassified win.

Logical execution is team selection, winner/venue lookup, conditional aggregation and ordering. The optimizer's actual plan is measured below.

## SQL query

```sql
-- Q12: Completed international-team wins by known venue/team country.
SELECT
    t.name AS team_name,
    SUM(CASE
        WHEN v.country_id = t.country_id THEN 1 ELSE 0
    END) AS home_wins,
    SUM(CASE
        WHEN v.country_id IS NOT NULL AND t.country_id IS NOT NULL
             AND v.country_id <> t.country_id THEN 1 ELSE 0
    END) AS away_wins,
    SUM(CASE
        WHEN m.match_id IS NOT NULL
             AND (v.country_id IS NULL OR t.country_id IS NULL)
        THEN 1 ELSE 0
    END) AS unclassified_wins
FROM teams AS t
LEFT JOIN matches AS m
    ON m.winner_team_id = t.team_id
   AND m.status = 'completed'
   AND m.result_type = 'win'
LEFT JOIN venues AS v ON v.venue_id = m.venue_id
WHERE t.is_international = 1
GROUP BY t.team_id, t.name
ORDER BY t.name ASC, t.team_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment defines completed wins for stored international-team classifications. |
| 2 | Begin selecting output fields. |
| 3 | Return the team name. |
| 4 | Begin conditional summation of home wins. |
| 5 | Add one when the venue and team have equal country IDs; otherwise add zero. |
| 6 | Name the home-win total. |
| 7 | Begin conditional summation of away wins. |
| 8 | Require both country identities to be known. |
| 9 | Add one for known unequal countries; otherwise zero. |
| 10 | Name the away-win total. |
| 11 | Begin a separate count for wins that cannot be geographically classified. |
| 12 | Require a real matched winning match, not the placeholder row from LEFT JOIN. |
| 13 | Test whether either the venue country or team country is unknown. |
| 14 | Add one only for such a real unclassifiable win, otherwise zero. |
| 15 | Name the additional coverage column unclassified_wins. |
| 16 | Start with every stored team. |
| 17 | Attach eligible wins without discarding teams with none. |
| 18 | Match a winning record to its winning team ID. |
| 19 | Require completed status. |
| 20 | Require a structured winning result. |
| 21 | Optionally resolve venue identity and its country; unknown venue remains visible. |
| 22 | Keep teams whose stored is_international classification is true. |
| 23 | Aggregate by team identity/name rather than merging equal names. |
| 24 | Sort teams alphabetically with an ID tie-breaker. |

## Running it and actual results

Load `sql/queries/q12_home_away_wins.sql` and execute SQLAlchemy `text(query)` within an existing read transaction. No parameters are required. There is no time-window or format restriction in the brief: it covers eligible wins in the selected stored dataset, not a verified all-time history.

| Fictional sample team | Home wins | Away wins | Unclassified wins |
| --- | ---: | ---: | ---: |
| Sample Australia XI | 17 | 18 | 0 |
| Sample India XI | 18 | 19 | 0 |

These reconcile with Question 5: 35 and 37 total wins respectively. For every selected team, home + away + unclassified equals its eligible completed winning-match count. A real country change or unusual representative region would require reliable stored team-country metadata; the query does not invent it.

Live output includes four teams marked international, all with zero eligible confirmed wins. All four lack a stored team country, venue-country coverage is incomplete, and structured winner/results have not been fully imported. The database also has one completed match with unresolved result metadata. Such missing results cannot enter the win counts or the unclassified-win bucket because a confirmed winning team is not known. Zero here is a stored confirmed-win count, not evidence of zero actual victories.

Source-scoped team identities remain separate and are not merged by matching names. A globally deduplicated or exhaustive international-team inventory is not claimed. Full outputs, coverage diagnostics and plans are in `11_q12_result.json`. No working records were changed and no API request was made.

## Actual SQLite execution plan

Both working databases show a scan of teams, a winner-ID lookup using `idx_matches_winner` for the LEFT JOIN, a venue primary-key lookup, and a temporary B-tree for final ordering. The international flag is applied as a team filter; no new international-flag index was added.

The existing winner index supplies each team's candidate wins. Status/result checks restrict eligibility, and the venue lookup supplies geographic evidence. No innings or player table is required. These observed SQLite plans are not PostgreSQL/MySQL execution verification.

## Optimization and common mistakes

Conditional aggregation computes all three counters in one grouped query instead of issuing separate home/away queries and merging them. Keep win eligibility in the LEFT JOIN's ON clause; putting it in WHERE would remove winless teams. Compare integer country IDs directly. Do not replace NULL country IDs with a common sentinel: two unknown countries must not become an apparent home match.

Use AND for both known-country checks before away inequality. Do not use ELSE 1 as a catch-all away definition. Avoid joining innings/performances, which can multiply winning matches, or grouping by team name alone, which can merge separate same-named identities. The defined grouping makes COUNT(DISTINCT match_id) unnecessary for this winner/venue access path.

No new schema/index change was justified. At larger scale, measure whether team eligibility filtering or winner/status/result lookup dominates before considering composite indexes or a maintained aggregate. Do not assume an index on a low-selectivity boolean flag will improve the report.

## Verification and checkpoint

The full suite passes **279 tests**; lint, formatting and whitespace checks pass. Six focused tests cover known home/away totals; zero-win teams with unknown country; missing team country, venue country and venue; neutral-country away classification; domestic/unfinished-result exclusion; draw/tie/no-result/pending exclusion; same-named team identities; and multi-innings matches counted once. All mutations occur in isolated temporary databases.

Question 12 is complete. Question 13 has not been implemented. Say **NEXT** to proceed to Question 13.
