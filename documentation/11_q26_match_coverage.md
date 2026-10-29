# Q26 — Saved match coverage (additional analysis)

Business question: which source, exact format and saved match status have imported matches and innings? This extra query satisfies the strict “25+” wording without replacing Q01–Q25.

Each output row represents one source/format/status group. The matches table supplies the population. Inner joins identify its source and format; a left join retains matches with no innings. COUNT(DISTINCT match_id) avoids inflating match counts when a Test has multiple innings. COUNT(DISTINCT innings_id) measures saved innings; the conditional match count measures matches having at least one innings. MIN/MAX show stored match-date coverage, not refresh time. GROUP BY preserves source and exact format; ORDER BY stabilizes presentation.

NULL date bounds mean dates are unknown. No innings does not establish that no real innings occurred. Retained old statuses can be stale: this is coverage of saved records, not the provider's current live list or a global completeness estimate. With incomplete imports, a zero joined-innings count is an observed absence in this database only.

Execution plan: scan/group the selected match population, resolve source/format primary keys and look up innings through its match relationship index. Review EXPLAIN QUERY PLAN on representative data before adding a wider composite index. This summary deliberately reads the full saved population, so a scan need not indicate a defect.

Test: the seeded sample has 72 distinct matches and 192 innings across three format groups, all completed. Summed counts must preserve those totals despite the one-to-many innings join. The query runs through the same restricted analytical reader as the original 25 questions.
