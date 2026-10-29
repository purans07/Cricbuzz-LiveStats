# Phase 11 — Question 15: batting contribution in close matches

## Business problem

The exact brief asks: “Identify players who perform exceptionally well in close matches. A close match is defined as one decided by less than 50 runs OR less than 5 wickets. For these close matches, calculate each player's average runs scored, total close matches played, and how many of those close matches their team won when they batted.”

The brief provides close-match thresholds but no numerical definition of exceptional performance or minimum sample size. Return all qualifying batting contributors and order by average runs; do not invent an extra cutoff or claim that a high average from a small sample establishes exceptional ability.

## Definitions before SQL

A close result must be completed with result_type='win' and a known conventional margin: runs < 50 OR wickets < 5, with each threshold checked against its unit. The schema already requires positive margin amounts. Exactly 50 runs or five wickets is excluded; 49 runs or four wickets qualifies. Draws, ties, no-results, pending results and wins without a conventional margin do not establish the requested condition. A super-over win without a run/wicket margin is not inferred to qualify.

Use only players with active batting records in those close matches. A squad/playing-XI entry with no batting record does not establish that the player batted. The importer already excludes did-not-bat scorecard placeholders; manual records must preserve that batting-record meaning. Missing entire batting innings still limits completeness.

Define average_runs as **average individual runs per qualifying match**: sum the player's ordinary innings within each match, then average those match totals. It is not runs per dismissal and not a mean of individual innings scores. Example: 20 and 30 in one match plus 10 in another gives (50+10)/2 = 30, not (20+30+10)/3 = 20. This uses the same per-match unit as the requested match/win counts.

If any included innings score is unknown, that player-match total is NULL. If any included match total is NULL, the final average remains NULL rather than an apparent mean over a subset. The match and win counts can still be known from the batting record and structured result. Known zero runs are retained.

## Concepts, tables and relationships

Use a CTE, two-stage GROUP BY, unit-specific OR conditions, SUM/AVG, CASE for completeness and conditional win counts, and stable ordering with explicit NULL placement.

`v_active_batting` filters deleted performance rows, deleted profiles and super overs. Its rows carry constrained player/match/innings/team identities. `matches` supplies completed status, result type, winner_team_id and typed margin. `players` supplies names. The player’s team comes from their performance in that match, not a current membership or inferred nationality.

## Logic and execution strategy before SQL

Filter match eligibility with completed AND win AND the grouped close-margin alternatives. Aggregate active batting innings to one player/match/team result. Preserve NULL when a score is missing. Then group those match units by player, calculate the mean, count matches and count matching batting-team/winner identities.

A player with several innings in a Test match contributes one match count and at most one team win. Players on the losing side remain in the batting comparison but receive no win credit. The schema prevents changing a player's team within a match. There is no format or time restriction in the question; these unnormalized per-match comparisons span the selected stored formats and should not be interpreted as format-adjusted ability scores.

The expected physical stages are active batting/match-result reads, first aggregation, player lookup, second aggregation and sort. The actual measured plan appears below.

## SQL query

```sql
-- Q15: Batting contribution per completed close match, then per player.
WITH close_player_matches AS (
    SELECT
        b.player_id, b.match_id, b.team_id, m.winner_team_id,
        CASE WHEN COUNT(*) = COUNT(b.runs)
             THEN SUM(b.runs)
        END AS match_runs
    FROM v_active_batting AS b
    JOIN matches AS m ON m.match_id = b.match_id
    WHERE m.status = 'completed'
      AND m.result_type = 'win'
      AND (
          (m.margin_unit = 'runs' AND m.margin_value < 50)
          OR (m.margin_unit = 'wickets' AND m.margin_value < 5)
      )
    GROUP BY b.player_id, b.match_id, b.team_id, m.winner_team_id
)
SELECT
    p.full_name AS player_name,
    CASE WHEN COUNT(*) = COUNT(q.match_runs)
         THEN ROUND(AVG(q.match_runs), 2)
    END AS average_runs,
    COUNT(*) AS total_close_matches_played,
    SUM(CASE WHEN q.team_id = q.winner_team_id THEN 1 ELSE 0 END)
        AS team_wins_when_batted
FROM close_player_matches AS q
JOIN players AS p ON p.player_id = q.player_id
GROUP BY p.player_id, p.full_name
ORDER BY (average_runs IS NULL) ASC, average_runs DESC,
         total_close_matches_played DESC, p.player_id ASC;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states the two-stage player/match then player aggregation. |
| 2 | Create a CTE for one player’s contribution in each qualifying close match. |
| 3 | Begin the match-level projection. |
| 4 | Keep player, match, historical batting-team and match-winner identities. |
| 5 | Only calculate a match run total if every included batting row has known runs. |
| 6 | Sum that player’s ordinary-innings runs within the match. |
| 7 | Name the nullable player-match total. |
| 8 | Read active ordinary-innings batting records. |
| 9 | Resolve the match result and margin. |
| 10 | Require completed status. |
| 11 | Require a structured winning result. |
| 12 | Begin the grouped OR conditions defining a close margin. |
| 13 | A runs victory qualifies only if its margin is strictly below 50. |
| 14 | Alternatively, a wickets victory qualifies only if its margin is strictly below five. |
| 15 | Close the paired unit-specific conditions. |
| 16 | Aggregate by player and match with its recorded team/winner identities. |
| 17 | End the match-level CTE. |
| 18 | Begin the final per-player projection. |
| 19 | Return the player name. |
| 20 | Require a known run total in every included close match before returning an average. |
| 21 | Average per-match run totals and round once to two decimals. |
| 22 | Name this per-close-match average. |
| 23 | Count the player-match rows, not innings or squad memberships. |
| 24 | Add one when the player’s recorded batting team won that match. |
| 25 | Name the conditional team-win count. |
| 26 | Read the qualifying player-match units. |
| 27 | Resolve the current displayed name by player identity. |
| 28 | Aggregate by identity/name, preserving separate same-named people. |
| 29 | Put known averages first, then larger averages. |
| 30 | Break ties by match count descending and player ID ascending. |

## Running it and actual results

Load `sql/queries/q15_close_match_batting.sql` and execute SQLAlchemy `text(query)` in an existing read transaction. No parameters, top-N limit or exceptional-performance threshold are required. Each selected database supplies its own stored match universe; equal names do not merge source-scoped identities.

The fictional sample returns 12 players. Its leading rows are:

| Player | Average runs per close match | Close matches batted | Team wins |
| --- | ---: | ---: | ---: |
| Sample Player 03 | 150.89 | 9 | 7 |
| Sample Player 04 | 144.67 | 9 | 7 |
| Sample Player 12 | 143.56 | 9 | 2 |

These are synthetic training performances, not factual professional statistics. Large combined match totals can include multiple innings by the same player.

The live result is empty. Detailed batting currently covers one ongoing Test, while the stored completed match has unresolved structured result/margin metadata and lacks detailed batting coverage. The query does not parse “won by 4 runs” from status text to fill those gaps. Empty output is insufficient qualifying stored evidence, not proof that no real player performs well in close games.

Full output, unresolved-result inventory and measured plans are in `11_q15_result.json`. Working datasets were read without changes. No API request was made.

## Actual SQLite execution plan and optimization

Both databases show a co-routine for close_player_matches, a batting scan through `idx_batting_player_match`, primary-key match/player/innings lookups for result and active-view checks, and a temporary B-tree for the match-level GROUP BY. SQLite then scans those units, resolves player names and uses temporary B-trees for the final grouping and ordering.

Keep the OR alternatives parenthesized beneath the completed/win filters; otherwise operator precedence can admit unrelated wicket results. Keep margin units paired with their numerical thresholds. Do not apply a universal margin < 50 to both units or use a current team membership for historical win credit.

Aggregate to match grain before AVG and COUNT. COUNT(DISTINCT match_id) by itself does not fix an innings-weighted average or repeated win sums. SUM/AVG ignore NULL by default, so completeness guards are necessary. Avoid joining all match players or bowling rows, which would multiply batting records.

No new index or schema change was introduced. At larger scale, benchmark result-first candidate selection versus the observed batting-first plan and consider indexes only with workload evidence. Complex OR eligibility and two aggregate levels cannot be assumed to disappear merely by adding a margin index. The recorded execution is SQLite-specific, not PostgreSQL/MySQL verification.

## Verification and checkpoint

The full suite passes **297 tests**; lint, formatting and whitespace checks pass. Six focused tests cover strict run/wicket boundaries; two innings counting as one match with a per-match average; unknown runs preserving match/win counts but not a partial average; unfinished/unresolved/drawn results and unknown margins excluded; deleted records/players and super overs excluded; and equal names with correct winning versus losing team credit. All test writes occur in isolated temporary databases.

Question 15 is complete. Question 16 has not been implemented. Say **NEXT** to proceed to Question 16.
