# Phase 9: API implementation completed

Phase 9's API integration milestone is complete. The selected provider is RapidAPI cricketapilive/cricbuzz-cricket, UI version v2. Its transport paths retain literal `v1` segments. Provider documentation was read directly at https://rapidapi.com/cricketapilive/api/cricbuzz-cricket on 22 October 2026. Phase 10 has not started.

## Implemented and verified

- Contract-bound HTTP client: private authentication, fixed HTTPS origin, safe errors, timeouts, bounded retries, response-size limits, gateway-mock checks, quota reporting and request intervals.
- Match-list normalization and transactional import, verified with an authenticated HTTP 200 response.
- Regular scorecard normalization and authenticated import for discovered match 147931. Correct innings/team relationships, follow-on order, did-not-bat exclusion and integer bowling-ball conversion are tested.
- Player profile normalization: provider ID, full name, role, batting style and bowling style. No birth-place-to-nationality inference or guessed representation dates.
- Aligned career batting/bowling import: three requests (profile, career batting, career bowling) precede one database transaction. A failure or inconsistent response imports nothing. Batting and bowling stay together in one career snapshot per format.
- Source-scoped identities, duplicate/stale detection, preservation of partial fields, overrides and tombstones, and database revision changes only on successful commits.
- Stored profile and latest-career reads, without HTTP calls.
- Explicit CLI commands for live matches, scorecards and individual players. Nothing refreshes automatically on page load.

The career-summary endpoint was also fetched successfully. It supplies debut/last-match references, not statistical totals. The series-match endpoint was verified successfully for series 11595: seven returned matches across ODI and Test formats. Its response is retained privately for coverage inspection, not passed through the match-list parser or stored as career statistics.

## Commands

```bash
.venv/bin/python -m api.cli check-config
.venv/bin/python -m api.cli sync-live --database data/runtime/live.db
.venv/bin/python -m api.cli sync-scorecard 147931 --database data/runtime/live.db
.venv/bin/python -m api.cli sync-player 8583 --database data/runtime/live.db
```

Each sync spends quota. A player sync uses three requests, separated by the configured interval. Use only explicitly selected player IDs; do not fetch all players automatically on the 200-request plan. Credentials load privately from `.env`; the commands never print them. The sample database stays separate.

## Career semantics

The observed provider table has Test, ODI, T20 and IPL columns. Test and ODI use their established format codes. T20 retains `INTERNATIONAL_T20`; official T20I eligibility is not asserted. IPL is a separate domestic T20 format; a zero-match IPL column creates no career row.

Dismissals equal batting innings minus explicit not-outs. Bowling `Balls` in the career table is a legal-ball count; it differs from encoded scorecard fields. Ratios with zero/unknown denominators are NULL, even when the provider prints `0.0`. Unknown catches and stumpings remain NULL. Highest-score asterisks are permitted; no not-out status is inferred from the numeric highest score.

Career requests expose no series-filter parameter in the production allowlist. Player IDs, response URLs, provider/version, mock flags, matching format columns, row widths, duplicate labels, counts and matching match totals are validated. The three requests must be within five minutes; their actual individual fetch times are included in the refresh result and sanitized captured fixtures. Their maximum fetch time labels the combined batch. This is a sequential bundle, not an assertion that the provider generated every statistic simultaneously.

## Acceptance evidence

See `09_phase_completion_result.json` for committed imports, capture times, mock flags, duplicate replay and integrity results. Six authenticated requests were used in this completion: profile, career summary, batting, bowling, regular scorecard and series matches. The final response reported 186 of 200 monthly requests remaining; this is an observed allowance, not a permanent quota guarantee.

The separate live database contains four matches, 12 innings, 22 players, 27 batting performances, 19 bowling performances and three career snapshots for Temba Bavuma. His Test row reports 68 matches, 3,993 runs and one wicket. Profile enrichment and career import committed atomically. Replay returned duplicate. Integrity and foreign-key checks passed.

Validation: 188 offline tests pass, including observed player-table mapping, malformed/provenance/scope rejection, duplicate replay, atomic failure preservation, CLI preflight, and all existing transport/ingestion tests. Ruff lint and formatting pass.

## Coverage limitations carried forward

This completes integration acceptance; it does not complete the real-data population required for every SQL question. Only one player's profile and career have been enriched. Fielding totals are absent from the tested career responses. Archive depth, globally complete player lists, venue capacities, structured toss/results and sufficient historical matches remain unmet data-coverage requirements. The tested series list is available through the configured client as raw provider JSON; a dedicated series importer/backfill is not implemented. None of those gaps are filled with fabricated records or inferred zeros.

The verified list, scorecard and player endpoints use single responses; no page query or continuation field was observed for them. The provider documents `lastId` pagination for series archives, which is not enabled or backfilled here. Generic cursor pagination remains tested, but that is not a claim that archive retrieval has been verified. Durable failed-batch history remains deferred: failed import transactions roll back entirely and return safe errors.

Phase 10 will implement CRUD after the user's confirmation. Q01–Q25 and dashboard pages retain their later phases.
