# Phase 11 — Question 24: successful adjacent batting pairs

## Assignment before SQL

For player pairs in consecutive batting positions (positions differ by one) appearing in at least five partnerships, calculate average runs, count partnerships exceeding 50, find the highest score, calculate the percentage of good partnerships and rank the most successful combinations.

## Scope and definitions before SQL

The available data records each batter's total innings score and batting position, not the runs added during an actual shared stand. Adjacent positions also do not prove that two batters were simultaneously at the crease. As in Question 13, this query implements the assignment's adjacent-position approximation: **combined individual innings runs**, explicitly a proxy rather than observed partnership runs. True stand analysis requires wicket/partnership or delivery data with both batters and stand boundaries; the current schema cannot reconstruct it reliably. Output names deliberately say combined runs and pair appearances.

One appearance is one unordered pair in one ordinary innings, in consecutive known batting positions. Self-join only within the same innings, and require the second position to equal the first plus one. This counts each adjacency once. Two innings in a Test can contribute two appearances; unlike Question 23 this question is at innings/pair grain. Aggregate across all stored matches and formats because the brief supplies no date, format or completed-status restriction. Live ordinary innings may contribute observed, changing scores; this is a snapshot of stored data, not necessarily finalized performances.

Canonicalize the player IDs with scalar MIN/MAX so the same two players remain one combination when batting order reverses. IDs, not names, identify pairs. Opposing teams and different innings cannot be combined. A deleted player or batting row disappears through `v_active_batting`; super overs are excluded. Missing positions do not establish adjacency. Do not use LEAD over surviving records: positions 1 and 3 must never become consecutive when position 2 is absent.

Require at least five **observed appearances**, including appearances with a missing score. Unknown individual runs make that combined score NULL, not zero. Show the number of known and missing scores. To avoid misleading comparisons, withhold all summary score metrics and the rank when any score is missing. Such qualifying pairs remain visible as `incomplete_scores`; missing scores do not silently reduce the denominator or pull the pair out of the minimum-five requirement. This rule cannot detect wholly absent imports; database coverage still matters.

Define a good appearance as combined runs **strictly greater than 50**, matching the question's supplied threshold. Exactly 50 is not good. Average = arithmetic mean of combined scores; highest = maximum; success percentage = 100 × good appearances / all appearances, only when score coverage is complete. Recorded zero scores remain valid observations.

## Ranking policy and concepts before SQL

The question gives no tie-breaking hierarchy. Use success percentage descending, then average combined runs descending, then highest combined runs descending. Use DENSE_RANK so identical raw metric triples share a rank without gaps. IDs stabilize display order only; they do not break metric ties. Rank before rounding percentages and averages. Sample size is displayed but is not an additional ranking key; five appearances can tie with a much larger history, so this is not a confidence-adjusted estimate.

Use CTEs for appearances, grouped summaries and eligible ranks; a self-join for exact adjacency; conditional aggregates and COUNT guards for completeness; and a left join to retain unranked incomplete combinations. `v_active_batting` provides active ordinary-innings rows. Its underlying innings constraint makes batting positions unique within an innings. `players` supplies the two display names. Career snapshots, team winners and bowling data are unnecessary.

Execution strategy: generate exact adjacent pairs first, canonicalize IDs, group at unordered pair grain, apply HAVING COUNT(*) >= 5, calculate complete metrics, dense-rank complete summaries, then attach labels and round for display. Do not filter scores above 50 before calculating the denominator, or count both directions of the same pair.

## SQL

```sql
-- Q24: Adjacent-position combined-score proxy, not observed stand runs.
WITH appearances AS (
    SELECT MIN(a.player_id,b.player_id) AS player_a_id,
           MAX(a.player_id,b.player_id) AS player_b_id,
           a.innings_id,a.runs+b.runs AS combined_runs
    FROM v_active_batting a
    JOIN v_active_batting b ON b.innings_id=a.innings_id
        AND b.batting_position=a.batting_position+1
), summaries AS (
    SELECT player_a_id,player_b_id,COUNT(*) AS pair_appearances,
           COUNT(combined_runs) AS known_scores,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN AVG(1.0*combined_runs) END AS average_combined_runs,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN SUM(combined_runs>50) END AS scores_above_50,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN MAX(combined_runs) END AS highest_combined_runs,
           CASE WHEN COUNT(combined_runs)=COUNT(*)
                THEN 100.0*SUM(combined_runs>50)/COUNT(*) END AS success_percentage
    FROM appearances GROUP BY player_a_id,player_b_id
    HAVING COUNT(*)>=5
), ranked AS (
    SELECT player_a_id,player_b_id,DENSE_RANK() OVER (
        ORDER BY success_percentage DESC,average_combined_runs DESC,
                 highest_combined_runs DESC
    ) AS success_rank
    FROM summaries WHERE known_scores=pair_appearances
)
SELECT r.success_rank,s.player_a_id,a.full_name AS player_a_name,
       s.player_b_id,b.full_name AS player_b_name,s.pair_appearances,
       s.known_scores,s.pair_appearances-s.known_scores AS missing_scores,
       ROUND(s.average_combined_runs,2) AS average_combined_runs,
       s.scores_above_50,s.highest_combined_runs,
       ROUND(s.success_percentage,2) AS success_percentage,
       CASE WHEN s.known_scores=s.pair_appearances THEN 'ranked'
            ELSE 'incomplete_scores' END AS coverage_status
FROM summaries s
JOIN players a ON a.player_id=s.player_a_id
JOIN players b ON b.player_id=s.player_b_id
LEFT JOIN ranked r ON r.player_a_id=s.player_a_id AND r.player_b_id=s.player_b_id
ORDER BY r.success_rank IS NULL,r.success_rank,s.player_a_id,s.player_b_id;
```

## Every line explained

| Line | Explanation |
| --- | --- |
| 1 | State that this is a combined-score proxy, not measured stand runs. |
| 2 | Begin the per-innings adjacent appearances. |
| 3 | Choose the smaller player ID as the canonical first identity. |
| 4 | Choose the larger ID as the canonical second identity. |
| 5 | Keep innings identity and add the two individual innings scores; NULL propagates. |
| 6 | Read active ordinary-innings batting rows for the first position. |
| 7 | Join another active batter in that exact innings. |
| 8 | Require the next numerical batting position, counting each adjacency once. |
| 9 | Begin pair-level summary aggregation. |
| 10 | Select pair identity and count all observed appearances. |
| 11 | Count appearances with a known combined score. |
| 12 | Require complete scores for the mean. |
| 13 | Compute a real-valued arithmetic mean of combined scores. |
| 14 | Require complete scores for the above-50 count. |
| 15 | Count only scores strictly exceeding 50. |
| 16 | Require complete scores for the maximum. |
| 17 | Find the highest combined score. |
| 18 | Require complete scores for the success percentage. |
| 19 | Divide above-50 count by all appearances using real arithmetic. |
| 20 | Aggregate all innings appearances by canonical player pair. |
| 21 | Keep combinations with at least five appearances. |
| 22 | Begin the complete-score ranking CTE. |
| 23 | Select pair identity and start dense ranking. |
| 24 | Order by success percentage, then average score, both descending. |
| 25 | Use highest score descending as the final metric tie-breaker. |
| 26 | Name the shared dense rank. |
| 27 | Rank only complete-score combinations. |
| 28 | Finish the CTE chain. |
| 29 | Select rank and first player identity and label. |
| 30 | Select the second player identity and appearance count. |
| 31 | Expose known-score and missing-score counts. |
| 32 | Round the average for display after ranking. |
| 33 | Display the good-appearance count and maximum score. |
| 34 | Round the percentage for display after ranking. |
| 35 | Label complete-score combinations as ranked. |
| 36 | Label the other qualifying combinations as incomplete. |
| 37 | Read all eligible summaries, including incomplete ones. |
| 38 | Attach the first player name by ID. |
| 39 | Attach the second player name by ID. |
| 40 | Attach rank when available without dropping incomplete summaries. |
| 41 | Show ranked pairs first, then use rank and stable IDs for display. |

## Running and observed results

Run the SQL on a read-only connection to the chosen sample or live database. There are no parameters or implicit current-date conditions. Re-run after imports to analyze a new stored snapshot; no API call is part of this lesson.

Sample returns ten qualifying pairs, all with complete scores. Sample Players 11/12 lead with 96 appearances, average combined runs 136.41, 94 scores above 50, highest 225 and success percentage 97.92%. These are fictional individual-score combinations, not real historical stands.

Live returns no qualifying combinations: no pair appears at least five times in the stored ordinary-innings scorecards. This does not establish that real players lack repeated partnerships; historical ingestion is limited.

The [execution report](11_q24_result.json) contains every row and actual SQLite query plans for both databases. Working databases were read only.

## Actual plan and optimization

```text
MATERIALIZE summaries
SCAN b
SEARCH i USING INTEGER PRIMARY KEY (rowid=?)
SEARCH b USING INDEX sqlite_autoindex_batting_performances_2 (innings_id=? AND batting_position=?)
SEARCH players USING INTEGER PRIMARY KEY (rowid=?)
SEARCH i USING INTEGER PRIMARY KEY (rowid=?)
SEARCH players USING INTEGER PRIMARY KEY (rowid=?)
USE TEMP B-TREE FOR GROUP BY
MATERIALIZE ranked
CO-ROUTINE (subquery-13)
SCAN summaries
USE TEMP B-TREE FOR ORDER BY
SCAN (subquery-13)
SCAN s
SEARCH a USING INTEGER PRIMARY KEY (rowid=?)
SEARCH b USING INTEGER PRIMARY KEY (rowid=?)
BLOOM FILTER ON r (player_a_id=? AND player_b_id=?)
SEARCH r USING AUTOMATIC COVERING INDEX (player_a_id=? AND player_b_id=?) LEFT-JOIN
USE TEMP B-TREE FOR ORDER BY
```

SQLite can use the unique innings/position index to find each next position and keyed player/innings joins behind the active view. The actual plan above records its chosen access paths and temporary grouping/ranking/order structures. The query reduces to pair summaries before running the ranking window; it avoids an all-player-combinations cross join. No additional index is warranted for the small current datasets. Never optimize by removing score-completeness guards or skipping numerical gaps.

## Validation and interpretation

Eight focused tests cover the five-appearance boundary, strictly greater-than-50 threshold, zero and missing scores, order reversal, numerical position gaps, deleted profiles and super overs, same-named identities and shared dense ranks, ranking success rate before mean, and same-innings scope. Full suite: 367 tests passed; lint, formatting and whitespace checks pass. Tests use temporary database copies.

Combining formats and unfinished innings can affect averages and ranks. Shared individual totals omit stand-specific extras, dismissals and overlap, and can overstate the runs actually made together. The rank is descriptive and does not prove chemistry or predict a future stand. A future exact partnership feature requires additional structured source data and storage.

Question 24 is complete. Question 25 awaits NEXT; Phase 11 remains in progress.
