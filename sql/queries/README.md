# Saved SQL analyses

Q01–Q25 implement the original brief; Q26 adds source/format/status coverage. Q22 has a separate venue breakdown. All are available in Analytics.

| Query | Source |
| --- | --- |
| Q01 | [q01_india_players.sql](q01_india_players.sql) |
| Q02 | [q02_recent_matches.sql](q02_recent_matches.sql) |
| Q03 | [q03_top_odi_run_scorers.sql](q03_top_odi_run_scorers.sql) |
| Q04 | [q04_large_venues.sql](q04_large_venues.sql) |
| Q05 | [q05_team_wins.sql](q05_team_wins.sql) |
| Q06 | [q06_players_per_role.sql](q06_players_per_role.sql) |
| Q07 | [q07_highest_score_per_format.sql](q07_highest_score_per_format.sql) |
| Q08 | [q08_series_started_2024.sql](q08_series_started_2024.sql) |
| Q09 | [q09_qualified_all_rounders.sql](q09_qualified_all_rounders.sql) |
| Q10 | [q10_last_completed_matches.sql](q10_last_completed_matches.sql) |
| Q11 | [q11_cross_format_batting.sql](q11_cross_format_batting.sql) |
| Q12 | [q12_home_away_wins.sql](q12_home_away_wins.sql) |
| Q13 | [q13_adjacent_batting_pairs.sql](q13_adjacent_batting_pairs.sql) |
| Q14 | [q14_bowling_by_venue.sql](q14_bowling_by_venue.sql) |
| Q15 | [q15_close_match_batting.sql](q15_close_match_batting.sql) |
| Q16 | [q16_yearly_batting.sql](q16_yearly_batting.sql) |
| Q17 | [q17_toss_decision_win_rate.sql](q17_toss_decision_win_rate.sql) |
| Q18 | [q18_limited_overs_economy.sql](q18_limited_overs_economy.sql) |
| Q19 | [q19_batting_consistency.sql](q19_batting_consistency.sql) |
| Q20 | [q20_format_matches_and_averages.sql](q20_format_matches_and_averages.sql) |
| Q21 | [q21_weighted_performance_rank.sql](q21_weighted_performance_rank.sql) |
| Q22 | [q22_head_to_head.sql](q22_head_to_head.sql) |
| Q22 | [q22_head_to_head_venues.sql](q22_head_to_head_venues.sql) |
| Q23 | [q23_recent_player_form.sql](q23_recent_player_form.sql) |
| Q24 | [q24_successful_batting_pairs.sql](q24_successful_batting_pairs.sql) |
| Q25 | [q25_quarterly_player_evolution.sql](q25_quarterly_player_evolution.sql) |
| Q26 | [q26_match_coverage.sql](q26_match_coverage.sql) |

Select an analysis to review its definitions and parameters. Results use saved records; absent provider history is not replaced with synthetic live facts. Source-specific career queries use latest committed snapshots. Partnership analyses are adjacent-batter combined-score proxies, not actual measured stands. Form/trajectory labels use documented heuristics.

SQLite is the query authoring dialect; reviewed translation and result equivalence were tested on PostgreSQL 14.21 and MySQL 9.5.0. Current local custom SQL is bounded and read-only; the public sample disables that interface.

Operational helpers dataset_status.sql and player_by_id.sql support mode/revision and bound identity reads. Detailed lessons remain in documentation/11_q*.md as dated learning records.
