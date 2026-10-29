# Phase 11 — Question 13: adjacent batting-position pairs

## Business problem

The exact brief asks: “Identify batting partnerships where two consecutive batsmen (batting positions next to each other) scored a combined total of 100 or more runs in the same innings. Show both player names, their combined partnership runs, and which innings it occurred in.”

The question explicitly defines the pair by batting-order adjacency and the sum of individual innings scores. **This is not an actual partnership total.** Actual partnership runs are scored while two batters are together at the crease and may include extras; individual totals span different partners. The output is therefore named combined_runs and must not be presented as a verified wicket-partnership record.

## Concepts, tables and relationships before SQL

Use a self-join with two aliases, a join condition requiring position + 1, addition, an inclusive threshold and joins for names/innings context. A self-join compares different rows of the same relation.

`batting_performances` has one row per innings/player, a unique `(innings_id, batting_position)` for known positions, and constrained match/team/player relationships. `v_active_batting` excludes deleted performance rows, deleted players and super overs. `players` supplies names. `innings` supplies the chronological innings_number within each match.

Local match_id and innings_id are returned to distinguish, for example, innings 1 of different matches. They are internal database identities, not provider match IDs to paste into API endpoints.

## Query logic and planned execution

For every active batting row a, find b in the same innings whose actual batting_position is a.batting_position + 1. Add their runs and keep sums >= 100. Resolve both names and innings context; order by combined sum with stable identity/position tie-breakers.

The directional +1 condition returns (1,2), (2,3), and so on without also returning reverse pairs. Adjacent qualifying pairs may overlap: positions 1/2 and 2/3 can both qualify. This is intended, not duplicate data. Nonadjacent pairs do not qualify even if they actually batted together or their sum is high.

Do not use LEAD over the filtered active rows without checking actual position difference: if position 2 is deleted, positions 1 and 3 must not become adjacent. Unknown position cannot establish adjacency. Unknown runs make the sum NULL and cannot establish the threshold. Known zero is retained and can form a valid sum with 100 or more from its neighbor.

The innings-ID condition prevents cross-match, cross-innings and cross-team combinations. Batting-side composite foreign keys already enforce that one innings belongs to one batting team. Same-named players remain separate identities. Test innings and follow-on order are not combined.

Conceptually, select an active batting row, look up its adjacent partner by innings/position, filter the sum, resolve names/context and sort. SQLite may choose another physical join order; its measured plan appears below.

## SQL query

```sql
-- Q13: Adjacent batting positions with combined individual innings runs >= 100.
SELECT
    a.match_id,
    a.innings_id,
    i.innings_number,
    p1.full_name AS player1_name,
    p2.full_name AS player2_name,
    a.runs + b.runs AS combined_runs
FROM v_active_batting AS a
JOIN v_active_batting AS b
    ON b.innings_id = a.innings_id
   AND b.batting_position = a.batting_position + 1
JOIN players AS p1 ON p1.player_id = a.player_id
JOIN players AS p2 ON p2.player_id = b.player_id
JOIN innings AS i ON i.innings_id = a.innings_id
WHERE a.runs + b.runs >= 100
ORDER BY combined_runs DESC, a.match_id ASC, a.innings_id ASC,
         a.batting_position ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states the literal adjacent-position/summed-individual-scores definition. |
| 2 | Begin selecting output fields. |
| 3 | Return the local match identity. |
| 4 | Return the globally unique local innings identity. |
| 5 | Return its chronological innings number within the match. |
| 6 | Return the earlier batting-position player’s name. |
| 7 | Return the immediately next batting-position player’s name. |
| 8 | Add the two individual innings scores; label this combined_runs. |
| 9 | Read active ordinary-innings batting rows as the first member a. |
| 10 | Self-join the same active-batting view as second member b. |
| 11 | Require both records to belong to the exact same innings ID. |
| 12 | Require b’s actual position to equal a’s position plus one. |
| 13 | Resolve the first player’s name by identity. |
| 14 | Resolve the second player’s name by identity. |
| 15 | Resolve the innings number for the output context. |
| 16 | Require a known combined score of at least 100; exactly 100 qualifies. |
| 17 | Sort largest combined score first, then by match and innings identities. |
| 18 | Use the earlier batting position to break remaining ties and end the statement. |

## Running it and observed output

Load `sql/queries/q13_adjacent_batting_pairs.sql` and execute SQLAlchemy `text(query)` in an existing read transaction. No parameters, date restriction, format restriction or top-N limit are required by the question. Results cover stored ordinary innings only.

The fictional sample returns **691 pairs**. These are simplified synthetic training scores, not realistic/factual professional partnerships. The highest sample sum is 227.

The live stored scorecard produces four pairs:

| Innings number | Earlier-position player | Next-position player | Combined individual runs |
| --- | --- | --- | ---: |
| 1 | Temba Bavuma | Matthew Breetzke | 183 |
| 1 | David Bedingham | Temba Bavuma | 179 |
| 1 | Marco Jansen | Simon Harmer | 167 |
| 3 | Travis Head | Marnus Labuschagne | 126 |

Bavuma's 179 plus Breetzke's 4 gives 183. It does not assert they scored 183 while together at the crease. All live pairs are from the one imported match's detailed batting records; this is not complete historical coverage. Imported batting positions are based on the observed provider batting list order; any future provider change in that ordering requires adapter verification.

Working data is separated by selected sample/live database. Distinct imported match identities from separate sources are not deduplicated as physical events. Complete outputs and plans are in `11_q13_result.json`. No API request or working-data modification was made.

## Actual SQLite execution plan and optimization

Both working databases show one batting access path scanning via the player/match index and an adjacent partner lookup through the unique `(innings_id, batting_position)` index. Expansion of each active-batting view performs player/innings primary-key checks for deletion and super-over filtering. Additional primary-key lookups obtain displayed names and innings context. A temporary B-tree sorts the final results.

The important partner access path is indexed equality on innings ID and the computed next position. Avoid an unrestricted self-cross-join followed by name comparisons, DISTINCT or grouping away errors. The directional adjacency join already prevents reverse duplicates and the unique position constraint ensures at most one partner per known position.

The sum threshold depends on both rows, so an index on runs alone does not establish qualifying pairs. Do not aggregate all innings runs or join match participation tables into the pair comparison. No new index or schema change was added; measure larger representative data before changing view expansion or access paths. The recorded plan is SQLite-specific, not PostgreSQL/MySQL verification.

## Verification and checkpoint

The full suite passes **285 tests**; lint, formatting and whitespace checks pass. Six focused tests cover 100 inclusive/99 excluded; overlapping adjacent pairs once each; separate innings never combined; deleted-position gaps, deleted players and super overs excluded; unknown runs/positions; and same-name identities without reverse duplicates. All mutations occur in temporary database copies.

Question 13 is complete. Question 14 has not been implemented. Say **NEXT** to proceed to Question 14.
