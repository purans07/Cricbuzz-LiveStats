# Phase 9: regular scorecard import

The user confirmed the regular scorecard route `/mcenter/v1/{matchId}/scard` and supplied an HTTP 200 response for match 147931 (South Africa vs Australia, second Test). The response was reconstructed from RapidAPI's expanded tree into JSON using its object/array counts. The tracked fixture contains cricket response data only; credentials are excluded.

The scorecard adapter requires the two previously stored participant names and provider IDs. It checks the response match URL, maps batting teams by their exact names, and uses the other verified participant for bowling. It never alternates teams by innings number, preserving follow-ons. A repeated player cannot appear for both sides. Unsupported dismissals, teams, duplicate innings/players, mocks and malformed values are rejected.

Empty zero-score batting rows are did-not-bat roster entries and do not create batting performances. Explicit `not out`, `batting` and `retired hurt` entries count as undismissed batting innings. The capture therefore yields 22 players, 27 batting records and 19 bowling records. Bowling legal balls are calculated from overs: 24.1 overs means 145 legal balls. The provider's encoded `balls` and `ballnbr` fields are not treated as legal-ball counts. Fielding credits, career totals, roles and player nationalities are not inferred. Provider declaration/follow-on flags conflict with the match-list capture and are not persisted as established facts.

The captured response was imported into `data/runtime/live.db` as batch 2; replay returned `duplicate`. Integrity check passed and foreign-key check returned no errors. This used no HTTP request. Its fetched timestamp records local processing of a user-supplied capture; it does not establish a locally observed HTTP fetch time or independent gateway mock verification. See `09_scorecard_import_result.json` for the import evidence.

For future explicit online refreshes, the CLI supports:

```bash
.venv/bin/python -m api.cli sync-scorecard 147931 --database data/runtime/live.db
```

This preflights the live database and stored participants before requesting the regular scorecard. It uses the private configured key and the existing transactional importer. The online scorecard command has not yet been exercised against the gateway; the adapter and database import were verified offline against the user's capture.

Validation: 172 tests passed; Ruff lint passed. Phase 9 remains in progress: profile/career and other planned capabilities still need provider evidence and implementation. Phase 10 has not started.
