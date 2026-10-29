# Phase 11 — Question 17: toss decision and match-win percentage

## Business problem

The exact brief asks: “Investigate whether winning the toss gives teams an advantage in winning matches. Calculate what percentage of matches are won by the team that wins the toss, broken down by their toss decision (choosing to bat first or bowl first).” This supplies descriptive toss-winner win proportions for each decision.

## Denominator and interpretation before SQL

Eligible matches have completed status, a known toss winner, a known bat/bowl decision, and a resolved result_type of win, draw, tie or no_result. A draw, tie or no-result is not a match win, so it remains in the denominator and contributes zero to the win numerator. This estimates wins among **all eligible resolved completed matches**, not a decisive-results-only rate. Abandoned-status matches and pending results are excluded. A completed no-result is included under this explicit policy, even if play evidence is limited.

For a winning result, equality between toss_winner_id and winner_team_id establishes the numerator. Nonwinning results have no winner under the schema constraint. A tie resolved into a final structured win counts according to that final winner; the query does not infer results from text.

Percentage = 100 × toss-winner match wins / eligible matches for that decision. Zero wins out of positive eligible matches is a real 0%. No eligible matches means an undefined percentage, represented by NULL. Return eligible_matches and the win numerator alongside the requested percentage so sample size and missing coverage remain visible.

The two groups are descriptive, not a causal test. Teams choose bat/bowl based on conditions, match formats and strategy. A percentage above 50 or a difference between choices does not by itself prove a toss advantage or that one choice is better. The sample is synthetic and cannot support any real-world inference.

## Concepts, tables and relationships

Use a VALUES CTE for the two categories, LEFT JOIN to preserve an empty category, COUNT of a real match key, conditional SUM, NULLIF, real division, ROUND and GROUP BY.

`matches` supplies match_id, status, toss_winner_id, toss_decision, winner_team_id and result_type. Toss and winner IDs are constrained to participating teams through match_teams. Comparing these IDs does not require joining team names, which could be identical. There is one row per match; no innings, player or venue join is needed.

## Logic and planned execution

Create bat and bowl category rows. Attach only eligible matches, count them and count winner/toss-winner equality, then compute the guarded percentage. Restrict eligibility in ON so categories without matches are not discarded by WHERE.

An unmatched LEFT JOIN row contains NULL match/toss/winner fields. COUNT(match_id) returns zero; equality is unknown and the CASE's ELSE contributes zero. COUNT(*) would wrongly give an empty group one eligible match. SUM(CASE...) rather than COUNT(CASE... ELSE 0 END) is important because COUNT would also count the non-null zero values.

Conceptually this reads two categories, finds eligible matches, aggregates and returns one row each. SQLite's actual plan is recorded below.

## SQL query

```sql
-- Q17: Toss-winner win percentage over completed, resolved-result matches.
WITH toss_options (toss_decision) AS (
    VALUES ('bat'), ('bowl')
)
SELECT
    d.toss_decision,
    COUNT(m.match_id) AS eligible_matches,
    SUM(CASE WHEN m.winner_team_id = m.toss_winner_id
             THEN 1 ELSE 0 END) AS toss_winner_match_wins,
    ROUND(
        100.0 * SUM(CASE WHEN m.winner_team_id = m.toss_winner_id
                         THEN 1 ELSE 0 END)
        / NULLIF(COUNT(m.match_id), 0), 2
    ) AS win_percentage
FROM toss_options AS d
LEFT JOIN matches AS m
    ON m.toss_decision = d.toss_decision
   AND m.status = 'completed'
   AND m.result_type IN ('win', 'draw', 'tie', 'no_result')
   AND m.toss_winner_id IS NOT NULL
GROUP BY d.toss_decision
ORDER BY d.toss_decision ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states the completed/resolved-outcome population. |
| 2 | Define a two-row decision catalogue as a CTE. |
| 3 | Create the valid bat and bowl decision categories, not fabricated match data. |
| 4 | End the CTE. |
| 5 | Begin selecting output columns. |
| 6 | Return the recorded toss decision code. |
| 7 | Count real eligible matched records; NULL placeholder rows do not count. |
| 8 | Begin counting whether the match winner equals the toss winner by team identity. |
| 9 | Add one for equality, otherwise zero; name this toss-winner win count. |
| 10 | Begin the rounded percentage expression. |
| 11 | Multiply the matching-win count by 100.0 to force real-number arithmetic. |
| 12 | Complete the same conditional numerator. |
| 13 | Divide by the eligible match count; NULLIF makes an empty denominator undefined. |
| 14 | Round to two decimals and name the win percentage. |
| 15 | Start with both decision categories so missing categories remain visible. |
| 16 | Optionally attach eligible match records. |
| 17 | Match the recorded toss decision to the category. |
| 18 | Require completed status. |
| 19 | Require a resolved winning or nonwinning result; exclude pending results. |
| 20 | Require a known toss-winning team. |
| 21 | Aggregate into one row per decision. |
| 22 | Sort bat before bowl alphabetically and terminate the statement. |

## Running it and observed results

Load `sql/queries/q17_toss_decision_win_rate.sql` and execute SQLAlchemy `text(query)` within an existing read transaction. No input parameter, date window or format restriction is specified. These groups summarize the selected stored dataset, not a synchronized global cricket population. Separate source-scoped match identities are not merged as the same physical event.

| Fictional sample decision | Eligible matches | Toss-winner match wins | Win percentage |
| --- | ---: | ---: | ---: |
| bat | 72 | 43 | 59.72 |
| bowl | 0 | 0 | NULL |

The seed chooses bat in every synthetic match. Therefore it has no bowl-first comparison group. The 59.72% is simply 43/72 × 100 rounded to two decimals, not evidence about professional cricket. Missing bowl examples are not evidence of a 0% win rate.

Both live categories have zero eligible matches and NULL percentages. Its stored completed match lacks required structured toss/result metadata. No toss choice was inferred from who batted first, a scorecard order or status prose. Complete outputs, eligibility coverage and plans are in `11_q17_result.json`. No API request or working-data modification was made.

## Actual SQLite execution plan and optimization

Both datasets scan the two constant category rows through a co-routine, then use `idx_matches_status_date` to locate completed candidates for the LEFT JOIN. A temporary B-tree supports GROUP BY. There is no separate final-sort step in the observed plan.

Keep the match grain; joining innings would multiply a match's vote. Team IDs provide reliable equality even for same-named teams. 100.0 prevents integer-truncation errors, and rounding is applied only after aggregation. Restricting eligibility to known toss/result data prevents missing winners from being silently treated as losses when the result is pending.

No new index or schema change was justified. For a large representative dataset, benchmark toss-decision/status lookup selectivity before considering a composite index; two categories and current small data do not establish an indexing bottleneck. VALUES syntax and the measured plan are verified on SQLite only, not PostgreSQL/MySQL execution.

A future analytical extension could compare decisive-result-only rates, stratify by format/venue/time and quantify uncertainty, but those are not silently substituted for this question's defined calculation.

## Verification and checkpoint

The full suite passes **309 tests**; lint, formatting and whitespace checks pass. Six focused tests cover bat/bowl counts and a noninteger percentage; resolved draws/ties/no-results in the denominator; pending/missing toss/decision exclusion; unfinished/abandoned status exclusion; empty groups with NULL rates; and team-ID comparison with multiple innings counting once. All test modifications occur in temporary databases.

Question 17 is complete. Question 18 has not been implemented. Say **NEXT** to proceed to Question 18.
