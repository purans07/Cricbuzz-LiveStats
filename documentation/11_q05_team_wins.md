# Phase 11 — Question 5: total wins for each team

## Business problem

The project brief asks: “Calculate how many matches each team has won. Show team name and total number of wins. Display teams with most wins first.” This produces a team-win summary over the selected stored dataset, including teams without a confirmed win.

## Concepts, tables and relationships before SQL

Use LEFT JOIN to retain all teams, COUNT of a non-null matched key for wins, GROUP BY for one result per team identity, and ORDER BY DESC for ranking. Conditions in ON restrict which matches are counted without removing teams that have none.

`teams.team_id` identifies a team. `matches.winner_team_id` references a participating team through the composite match_teams relationship. `matches.match_id` is the match primary key. `status` and `result_type` distinguish completed winning results from live/pending matches, ties, draws and no-results. The winner constraint requires a non-null winner only for result_type='win'.

## Query logic and planned execution

Start with all teams. Attach only matches whose winner is that team, whose status is completed and whose structured result is a win. Count matched match IDs, group by team ID/name, then sort largest win count first. Team name and ID resolve ties deterministically.

Count each match once. Do not join innings or performances, which could multiply one Test match across several rows. Do not count toss winners as match winners. Draws, ties and no-results do not award a match win. A tie resolved by a super over counts if the final structured match result is recorded as a win. The absence of a conventional margin does not prevent a valid win.

The expected execution reads teams, looks up eligible matches by winner ID, aggregates counts and sorts the result. The measured SQLite plan below verifies the actual index selection.

## SQL query

```sql
-- Q05: Count confirmed completed wins in the selected stored dataset.
SELECT
    t.name AS team_name,
    COUNT(m.match_id) AS total_wins
FROM teams AS t
LEFT JOIN matches AS m
    ON m.winner_team_id = t.team_id
   AND m.status = 'completed'
   AND m.result_type = 'win'
GROUP BY t.team_id, t.name
ORDER BY total_wins DESC, t.name ASC, t.team_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment limits the result to confirmed completed wins in the stored dataset. |
| 2 | Begin the output projection. |
| 3 | Return the team name as team_name. |
| 4 | Count non-null matched match IDs, naming the result total_wins. An unmatched team returns zero. |
| 5 | Start from teams so teams without wins remain eligible. |
| 6 | Attach matching wins while retaining unmatched teams. |
| 7 | A match belongs to this team's win count only when its winner ID equals the team ID. |
| 8 | Count completed matches only, excluding provisional results on unfinished matches. |
| 9 | Require the structured result_type to be win. |
| 10 | Aggregate by the team identity and name; equal names do not merge distinct teams. |
| 11 | Sort by wins descending, then alphabetically by team name and finally by team ID. |

## Why COUNT and ON placement matter

With a LEFT JOIN, an unmatched team still produces one output candidate containing NULL match columns. COUNT(*) would count that row and incorrectly report one win. COUNT(m.match_id) ignores NULL and correctly reports zero.

The completed/win restrictions belong in the join's ON clause. Putting them in WHERE would reject the NULL match rows and remove teams with no wins. COUNT(DISTINCT m.match_id) is unnecessary here: each match has one winner and is joined directly, with no extra one-to-many relationship.

## Running it and observed output

Load `sql/queries/q05_team_wins.sql` and execute with SQLAlchemy `text(query)` inside an existing read transaction. No input parameters are required. There is no date or format restriction in this question: count all eligible stored matches. These are dataset totals, not independently verified all-time career totals.

The unchanged sample returns:

| team_name | total_wins |
| --- | ---: |
| Sample India XI | 37 |
| Sample Australia XI | 35 |

These 72 winning results are fictional training data. In the live database, eight teams return zero confirmed wins. Its one completed match still has result_type='pending' and no structured winner, although status prose may describe the outcome. The importer deliberately did not infer a winner from prose. Zero here means zero **eligible stored wins**, not zero real-world victories or proof that a team lost every match. Complete results require structured winner enrichment and sufficient match history.

The query groups source-scoped team identities separately. Same-named teams from different sources are not assumed to be one team; globally deduplicated totals are not claimed. Physical database selection keeps synthetic and live datasets separate.

Complete results and the unresolved-result inventory are in `11_q05_result.json`. No API call or working-data modification was made.

## Actual SQLite plan and optimization

Both working databases report a scan of teams followed by `SEARCH m USING INDEX idx_matches_winner (winner_team_id=?) LEFT-JOIN` and a temporary B-tree for final ordering. The existing winner index supports the equality lookup; status/result restrictions are additional eligibility checks. Country, player and innings tables are not required for this question.

Keep the join on integer identities. Avoid matching names or parsing status_text. The primary-key match grain makes duplicate-removal work unnecessary. GROUP BY includes the selected name as well as the identity rather than relying on a dialect's loose grouping behavior. Every team must be examined to include winless teams, and the computed aggregate generally needs a final sort.

No index or schema change was added. If representative larger data makes this frequent report slow, benchmark a composite winner/status/result index or maintained aggregate rather than assuming improvement. Those options have write/storage costs and require workload evidence. The observed SQLite plan is not PostgreSQL/MySQL compatibility verification.

## Verification and checkpoint

The full suite passes **241 tests**; lint, formatting and whitespace checks pass. Five dedicated tests cover known ordered totals and zero-win teams; unfinished winning-result exclusion; draw/tie/no-result/pending exclusion; several innings still counting as one match; and equal team names preserving separate identities. Tests mutate only temporary database copies. Working sample/live databases were read without changes.

Question 5 is complete. Question 6 has not been implemented. Say **NEXT** to proceed to Question 6.
