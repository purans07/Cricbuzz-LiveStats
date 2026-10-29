# Live-match verification on 22 October 2026

One authenticated request to the confirmed cricketapilive live-match URL returned HTTP 200 at 06:30:44 UTC (12:00:44 Asia/Kolkata). The response was not marked as a RapidAPI gateway mock. Credentials were loaded privately and never displayed.

The response normalized and committed to data/runtime/live.db: four matches, eight teams, four venues, three series and 12 innings. The import inserted 45 entity records in batch 1. The database is live mode, schema 2, revision 1, with foreign keys enabled and integrity ok. This list contains records with different match states; it does not mean all four are currently ongoing.

RapidAPI response headers reported a 200-request allowance and 195 remaining at the time of this request. No additional network request was made during tests.

The original Phase 8 sample database remains separate. The current .env sample target is not silently switched to live mode. The raw response is retained privately under the ignored data/raw folder. Safe metadata is in 09_live_smoke_result.json.

## Reusable command

```sh
.venv/bin/python -m api.cli sync-live --database data/runtime/live.db
```

This explicitly checks an existing schema-2 live database before fetching, normalizes through the observed v2 adapter, and imports atomically. It will reject a sample or missing target before using quota. Each successful invocation performs one configured live-list request; do not run it repeatedly merely to inspect existing data.

The full test suite passes 164 checks, including database preflight and an injected-transport test of this command. Live-match transport, normalization and database ingestion are now verified together. The full Phase 9 milestone still needs detailed scorecard/player/career and series capability verification. Only the live_matches request is configured.

Next needed contract: the exact scorecard request URL from the selected listing, using returned match ID 147931. The interface label alone does not establish the transport path. No guessed route will be enabled.
