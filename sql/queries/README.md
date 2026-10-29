# Stored query definitions

Current operational queries:

- dataset_status.sql reads mode and revision.
- player_by_id.sql retrieves one active profile using a bound player_id parameter.

The two operational files are database-support definitions. Phase 11 now includes q01_india_players.sql, using a bound as_of_date parameter. Its lesson and observed results are in documentation/11_q01_india_players.md and documentation/11_q01_result.json. Q02–Q25 remain pending; advance only on NEXT.

Question 2: q02_recent_matches.sql uses window_start and as_of_utc canonical UTC parameters. Its full lesson and measured plan are in documentation/11_q02_recent_matches.md. Q03–Q25 remain pending.

Question 3: q03_top_odi_run_scorers.sql binds source_name and ranks the latest committed ODI career snapshots. The full lesson is documentation/11_q03_top_odi_run_scorers.md. Q04–Q25 remain pending.

Question 4: q04_large_venues.sql returns all stored venues with capacity strictly above 50,000. No parameters are required. Lesson: documentation/11_q04_large_venues.md. Q05–Q25 remain pending.

Question 5: q05_team_wins.sql counts completed structured wins for every stored team, including zero-win teams. No parameters. Lesson: documentation/11_q05_team_wins.md. Q06–Q25 remain pending.

Question 6: q06_players_per_role.sql counts active players per defined playing role, including zero-player roles. No parameters. Lesson: documentation/11_q06_players_per_role.md. Q07–Q25 remain pending.

Question 7: q07_highest_score_per_format.sql binds source_name and returns Test/ODI/T20I maxima from latest career highest scores, retaining NULL for missing formats. Lesson: documentation/11_q07_highest_score_per_format.md. Q08–Q25 remain pending.

Question 8: q08_series_started_2024.sql returns 2024-starting series, one row each, with ordered host/format display lists and original planned totals. SQLite; no parameters. Lesson: documentation/11_q08_series_started_2024.md. Q09–Q25 remain pending.

Question 9: q09_qualified_all_rounders.sql binds source_name and finds canonical all-rounders with runs > 1000 AND wickets > 50 within each latest career-format snapshot. Lesson: documentation/11_q09_qualified_all_rounders.md. Q10–Q25 remain pending.

Question 10: q10_last_completed_matches.sql returns up to twenty completed matches with known completion times first and nullable result/location metadata. No parameters. Lesson: documentation/11_q10_last_completed_matches.md. Q11–Q25 remain pending.

Question 11: q11_cross_format_batting.sql binds source_name and compares latest career runs across Test/ODI/T20I, requiring two played target formats and a pooled dismissal-based average. Lesson: documentation/11_q11_cross_format_batting.md. Q12–Q25 remain pending.

Question 12: q12_home_away_wins.sql counts international-team completed home/away wins, preserving zero-win teams and separately flagging unknown-country wins. No parameters. Lesson: documentation/11_q12_home_away_wins.md. Q13–Q25 remain pending.

Question 13: q13_adjacent_batting_pairs.sql finds consecutive-position batters in one ordinary innings with combined individual scores >= 100. These are not actual wicket-partnership totals. No parameters. Lesson: documentation/11_q13_adjacent_batting_pairs.md. Q14–Q25 remain pending.

Question 14: q14_bowling_by_venue.sql aggregates bowling to qualifying matches before venue analysis, requiring >=24 legal balls per match and >=3 matches; mean economy is an arithmetic match mean. No parameters. Lesson: documentation/11_q14_bowling_by_venue.md. Q15–Q25 remain pending.

Question 15: q15_close_match_batting.sql analyzes players who batted in completed wins by <50 runs OR <5 wickets, averaging per-match run totals and counting historical team wins. No parameters. Lesson: documentation/11_q15_close_match_batting.md. Q16–Q25 remain pending.

Question 16: q16_yearly_batting.sql reports yearly match-based runs and mean strike rates since 2020, requiring five evidenced appearances within a UTC start year. SQLite; no parameters. Lesson: documentation/11_q16_yearly_batting.md. Q17–Q25 remain pending.

Question 17: q17_toss_decision_win_rate.sql reports toss-winner win percentages by bat/bowl choice, with eligible denominator counts and NULL for empty groups. Completed resolved nonwinning outcomes remain in the denominator. SQLite; no parameters. Lesson: documentation/11_q17_toss_decision_win_rate.md. Q18–Q25 remain pending.

Question 18: q18_limited_overs_economy.sql ranks pooled ODI/T20 economy with >=10 bowled matches and a two-over average workload, preserving unknown metrics. No parameters. Lesson: documentation/11_q18_limited_overs_economy.md. Q19–Q25 remain pending.

Question 19: q19_batting_consistency.sql calculates mean/population deviation of known ordinary-innings scores with >=10 balls faced and match starts since 2022. SQLite SQRT verified; no parameters. Lesson: documentation/11_q19_batting_consistency.md. Q20–Q25 remain pending.

Question 20: q20_format_matches_and_averages.sql binds source_name and pivots latest international Test/ODI/T20 career match counts/averages with >=20 known matches and T20-overlap rejection. Lesson: documentation/11_q20_format_matches_and_averages.md. Q21–Q25 remain pending.

Question 21: q21_weighted_performance_rank.sql binds source_name, applies the exact weighted career formula and dense-ranks complete scores per format. Missing fielding/undefined averages are not zero. Lesson: documentation/11_q21_weighted_performance_rank.md. Q22–Q25 remain pending.

## Q22 — Head-to-head history

`q22_head_to_head.sql` returns one row per qualifying pair/team. `q22_head_to_head_venues.sql` returns venue/actual-first-innings groups for those same pairs. Bind normalized UTC `window_start` inclusive and `window_end` exclusive, three calendar years apart. At least five completed fixtures are required across venues. Pending outcomes suppress percentages; run and wicket margins stay separate. See [the lesson](../../documentation/11_q22_head_to_head.md). Q23 awaits NEXT.

## Q23 — Recent player form

`q23_recent_player_form.sql` takes `as_of_utc` (normalized UTC, exclusive match-start cutoff). It aggregates ordinary innings into completed batting matches, compares the newest five/ten per active player and reports pooled strike rates, above-50 match totals, population deviation and heuristic form labels. Ten matches and complete metrics are needed for classification. All formats are combined; thresholds and limitations are in [the lesson](../../documentation/11_q23_recent_player_form.md). Q24 awaits NEXT.

## Q24 — Successful adjacent batting pairs

`q24_successful_batting_pairs.sql` requires no parameters. It groups unordered adjacent-position pairs within ordinary innings, requires five appearances and ranks complete combined-score summaries by success percentage, mean and maximum. Good means strictly above 50; missing scores leave a qualifying pair unranked. This is a proxy, not measured partnership runs. See [the lesson](../../documentation/11_q24_successful_batting_pairs.md). Q25 awaits NEXT.

## Q25 — Quarterly player evolution

`q25_quarterly_player_evolution.sql` binds `window_start` inclusive and `window_end` exclusive as normalized UTC whole-quarter boundaries spanning twelve completed quarters. It requires six observed quarters and three batting matches in every observed quarter, then reports mean match runs/rates, calendar-adjacent changes and centered OLS slopes with documented heuristic phases. Missing metric histories remain unclassified; gaps are not zero-filled. See [the lesson](../../documentation/11_q25_quarterly_player_evolution.md). All Q01–Q25 are complete; Phase 12 is pending the user's request.

## Additional analysis

[Q26: saved match coverage](../../documentation/11_q26_match_coverage.md) summarizes matches/innings by source, exact format and saved status. It preserves the original 25 questions unchanged.
