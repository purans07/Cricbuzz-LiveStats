# Phase 11 — Question 10: last twenty completed matches

## Business problem

The exact brief asks: “Get details of the last 20 completed matches. Show match description, both team names, winning team, victory margin, victory type (runs/wickets), and venue name. Display most recent matches first.” This creates a recent-results listing with explicit result metadata.

## Concepts, tables and relationships before SQL

Use WHERE to select completed status, repeated table aliases for different team roles, inner joins for the two required participants, LEFT JOIN for optional result/location data, ORDER BY for chronology and LIMIT for up to twenty rows.

`matches` supplies description, status, start/completion timestamps, winner_team_id, margin_value, margin_unit and venue_id. `match_teams` links each match to its two participants through unique slots 1 and 2; `teams` supplies names. The winner is another reference to a team, constrained to a match participant. `venues` supplies the venue name.

A match, not an innings or player performance, is the output grain. No innings join is needed. The participant-slot uniqueness constraints avoid multiple combinations and one-to-many duplication.

## Logic, chronology and planned execution

Select stored matches with status completed. Resolve both participant slots, then optionally resolve winner and venue. Keep draws, ties, no-results and completed matches with unresolved metadata; completed does not imply that a winner exists.

Sort known actual completion timestamps descending. Unknown completion timestamps follow all known ones, using start time descending within that undated group. Match ID breaks remaining ties. This explicitly retains undated completions without claiming a scheduled start/end is an actual completion time. It is **not** guaranteed true recency when completion data is missing: an undated match may in reality be newer than dated matches. Once completion metadata is populated, that limitation is reduced. Unknown start times also sort after known starts within tied completion groups under the tested SQLite descending order.

The brief does not request a time-window cutoff; this query uses the latest stored completed state, not an as-of historical view or “last 30 days.” LIMIT 20 means at most twenty available joined matches, not a guarantee that twenty have been imported.

Chronological completeness and identity completeness are separate: an invalid/missing participant slot would exclude a match through the inner joins. Valid imported matches are checked to have two participants. Optional venue/winner fields do not remove a match.

Conceptually: status filter, participant/result/location lookups, ordering, then limit. The physical plan is inspected below rather than assumed.

## SQL query

```sql
-- Q10: Up to twenty stored completed matches; known completion times first.
SELECT
    m.description AS match_description,
    t1.name AS team1_name,
    t2.name AS team2_name,
    winner.name AS winning_team,
    m.margin_value AS victory_margin,
    m.margin_unit AS victory_type,
    v.name AS venue_name
FROM matches AS m
JOIN match_teams AS mt1 ON mt1.match_id = m.match_id AND mt1.slot = 1
JOIN teams AS t1 ON t1.team_id = mt1.team_id
JOIN match_teams AS mt2 ON mt2.match_id = m.match_id AND mt2.slot = 2
JOIN teams AS t2 ON t2.team_id = mt2.team_id
LEFT JOIN teams AS winner ON winner.team_id = m.winner_team_id
LEFT JOIN venues AS v ON v.venue_id = m.venue_id
WHERE m.status = 'completed'
ORDER BY (m.completed_at IS NULL) ASC,
         m.completed_at DESC, m.starts_at DESC, m.match_id DESC
LIMIT 20;
```

## Every SQL line explained

| File line | Meaning |
| --- | --- |
| 1 | Comment states the limit and the explicit unknown-completion-time ordering policy. |
| 2 | Begin selecting output fields. |
| 3 | Return the match description. |
| 4 | Return the participant in slot 1 as team1_name. |
| 5 | Return the participant in slot 2 as team2_name. |
| 6 | Return the structured winner name, or NULL when none is supplied. |
| 7 | Return the stored numerical victory margin, preserving unknown values. |
| 8 | Return its unit, runs or wickets, without inferring it from prose. |
| 9 | Return the venue name, or NULL when unknown. |
| 10 | Read matches with alias m. |
| 11 | Resolve the unique first team slot for this match. |
| 12 | Look up that participant’s name. |
| 13 | Resolve the unique second team slot for the same match. |
| 14 | Look up the second participant’s name. |
| 15 | Optionally resolve the structured winner; draws, ties and missing winner data remain visible. |
| 16 | Optionally resolve the venue without excluding matches lacking it. |
| 17 | Include completed status only, regardless of whether its result metadata has been enriched. |
| 18 | Sort known completion times before unknown ones: IS NULL is false/zero for a known value. |
| 19 | Within those groups, sort completion time newest first, then start time and match ID descending. |
| 20 | Return at most twenty joined eligible match records. |

## Result semantics

Victory margin is numeric, and victory type is its separate unit: for example, 25 and runs, or 3 and wickets. Do not add or compare those units as if they were interchangeable. A final winner can be known even when a conventional run/wicket margin is absent, such as some super-over decisions. The query preserves those NULLs.

For draw/tie/no-result rows, winner and conventional margin are NULL. A completed row with unresolved result_type='pending' also retains NULL metadata. The requested seven columns do not distinguish these causes; a future dashboard should include the stored result/status context when explaining missing outcomes. This query does not invent labels such as “draw” from NULL alone or parse winner names from status_text.

The winner and venue joins are LEFT JOINs so missing metadata cannot remove an otherwise eligible result. The two participant joins use their slots, not alphabetical order or the winning team position. There is no GROUP BY or DISTINCT because each joined relationship is at most one matching row per match.

## Running it and observed outputs

Load `sql/queries/q10_last_completed_matches.sql` and execute SQLAlchemy `text(query)` inside an existing read transaction. No input parameters are needed. It queries the selected stored dataset; separate source-scoped match identities are not deduplicated as real-world events across providers.

- Sample: twenty fictional matches from 72 completed records, all with known completion timestamps and structured results. The first is Synthetic match 072: Sample India XI vs Sample Australia XI, won by Sample Australia XI by 168 runs, at Sample Ground 1.
- Live: one stored completion, 4th Match, Tasmania vs Victoria at Bellerive Oval. Structured winner, margin/type and completion timestamp are unknown. Its status text may describe a result, but that is not used as a substitute for structured metadata. This is not a complete recent-worldwide-results list.

Full twenty-row sample output, the live row, completion/result coverage and plans are in `11_q10_result.json`. Working databases were only read. No API request was used.

## Actual SQLite execution plan and optimization

Both working databases used `idx_matches_status_date` for status='completed'. SQLite used the unique match_id/slot index for both participants and primary-key lookups for team, winner and venue names. A temporary B-tree sorted the final joined rows.

The existing status/completed_at index does not eliminate every part of this requested order: explicit NULL grouping and the start-time/ID tie-breakers still require sorting in the observed plan. LIMIT does not mean the database can necessarily skip identifying and ordering other candidate rows.

Keep identity-based joins and the completed-status filter; avoid deriving recency from formatted display strings or inferring a completion date with COALESCE(starts_at,scheduled_end). Do not join all innings to retrieve team names. Such a join would duplicate Test matches and distort the limit.

No index or schema change was introduced. At larger scale, measure whether a covered ordering strategy or a candidate-selection subquery helps. Selecting twenty matches before required participant joins can produce fewer than twenty valid rows if some candidates have incomplete participants; any rewrite must preserve this query's eligibility and output grain. Current small-table behavior does not justify speculative indexes. PostgreSQL/MySQL execution is not verified.

## Verification and checkpoint

The full suite passes **267 tests**; lint, formatting and whitespace checks pass. Six focused tests cover twenty-row completion ordering; completed-only eligibility; retention of draw/tie/no-result/pending outcomes; team slots and runs/wickets margins; optional venue; actual completion versus start-time order; undated completions; stable ties; and multiple innings without duplicate matches. Test writes occur only in isolated temporary databases.

Question 10 is complete. Question 11 has not been implemented. Say **NEXT** to proceed to Question 11.
