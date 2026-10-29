# Phase 12 — Page 6: Settings and phase completion

All six Phase 12 pages are implemented: Home, Live Matches, Top Players, Analytics, CRUD and Settings. Phase 13 has not started. Chart requirements and wider live-data population remain pending their milestones; completing the page workflow does not claim those features are finished.

## Purpose and concepts explained before implementation

Settings makes the application's operational state understandable without exposing private configuration or silently changing permissions. It checks existing database availability, explains access policy, reports API configuration readiness without authenticating, and lets a user change timestamp display in their own browser session.

Separate trusted deployment configuration from harmless presentation preferences. DATA_MODE, DATABASE_URL and APP_ACCESS_MODE stay in operator-controlled configuration. API credentials remain private. A session-only display timezone may override the configured display value, but cannot change the database path, access mode, provider or credentials.

## Components, inputs and outputs

| Component | Input | Output |
| --- | --- | --- |
| Navigation | Settings | Sixth registered page |
| Recheck local status | Button | Rerun local reads; no HTTP request |
| Display timezone | Configured timezone or common IANA timezone | Session-only timestamp display preference |
| Apply for this session | Form submission | Preference used by pages on their next rerun |
| Reset | Form submission | Remove preference and use configured timezone |
| Current-time preview | Current UTC clock and effective timezone | Example localized timestamp |
| Database to inspect | Configured database, Saved sample, Saved provider | Readability/mode/schema status, revision and saved entity counts |
| Access policy | Trusted configuration | Local operator or public read-only, with capability explanation |
| API readiness | Private existing API settings loader | Configuration present/valid versus incomplete/invalid |
| Refresh policy | Validated non-secret policy values | Timeouts, attempts, operation budget and interval/cooldown explanation |
| Setup/privacy help | Bundled copy | Direction to Home's setup guides and explicit privacy boundaries |

The timezone list includes the configured value, Asia/Kolkata, UTC, Europe/London, Australia/Sydney, Africa/Johannesburg and America/New_York. These are display choices, not provider timezones or database storage changes. Public-readonly visitors may change their own display preference, but cannot change access rights.

## Backend and database calls

```text
Settings route -> render_settings
  -> load validated trusted application settings
  -> apply session-only display preference
  -> inspect selected existing target with database_health
  -> OverviewService read-only counts/revision/import metadata
  -> read supported schema version with PRAGMA user_version
  -> close/dispose resources
  -> privately load/validate API configuration
  -> return only allowlisted readiness and policy values
```

`services/settings_status.py` delegates entity counts and dataset metadata to OverviewService. Its database health helper opens an existing target through the existing central Database manager, which validates dataset mode, supported schema and query-only reads. It returns available=False for missing/unreadable/incompatible targets and always disposes the database. It never initializes, repairs or migrates a file. The mode/revision/count overview and schema-version lookup use read transactions; the overall diagnostics are lightweight checks, not a full integrity audit or a single immutable transaction across every diagnostic.

The page can inspect the configured custom path or the fixed project sample/live paths, preserving access settings. Inspection does not change the dataset selected on another page. A preserved schema-1 sample is valid for reads; live refresh still requires schema 2. Unsupported/mismatched targets are not labeled healthy. Actual zeros in a readable database differ from an unavailable database.

No raw connection URL, absolute private path or original database exception is rendered. Access policy is displayed from trusted configuration with no editable permission control. Local mode supports administrative forms and restricted custom SQL; public-readonly disables custom SQL and provider/CRUD writes through existing service checks.

## API readiness, not authentication

`api_readiness()` uses the existing API configuration loader, which validates the reviewed manifest, provider contract, policy and presence/shape of a private credential. It does not instantiate a transport client, send HTTP, test a subscription, check remaining quota or assert that data is fresh.

The returned dictionary contains only configured, provider, version and selected numerical policy fields. It never contains api_key, key fragments, request headers, base URL, manifest path, raw environment values or exception details. Invalid/missing configuration returns configured=False. An operator who wants live acceptance uses the deliberate refresh workflow on Live Matches.

The policy section distinguishes contract minimum interval from the dashboard's minimum 30-second shared coordinator delay. Retry-After may extend that delay. Coordination is process-local and resets on restart; it is not provider quota enforcement or a multi-instance scheduling guarantee. Automatic polling is not enabled.

## Session preferences and reruns

`ui/preferences.py` validates an optional session timezone with ZoneInfo and returns a replaced immutable Settings object containing only the display change. Invalid session values are ignored, falling back to trusted configuration. Every existing page now applies this helper after its own load_settings call. This preserves test injection points and all authoritative target/access fields.

Apply/Reset are form actions and only update Streamlit session state. The updated preference is reflected immediately on Settings and on other pages when they next rerun. A new/reconnected browser session may lose it. The page never edits .env, .streamlit/secrets.toml or the deployment configuration. Analytics dates and SQL parameters stay explicitly in UTC; a display preference does not shift analytical windows or stored timestamps.

The page is intentionally uncached. Recheck rereads current local state and configuration without HTTP. Database errors do not suppress the separate API-configuration explanation. Invalid application configuration shows a safe setup message and still allows the API-readiness section to render.

## Files created and changed

- `services/settings_status.py`: allowlisted local database/API diagnostics.
- `ui/preferences.py`: session-only display override.
- `ui/settings.py`: diagnostics, timezone form, policy and setup guidance.
- `pages/06_Settings.py`: thin route.
- All five existing UI modules: shared display-preference application.
- `main.py` and Home roadmap: all six completed pages and Phase 13 preview.
- `tests/test_settings_page.py`: diagnostics, privacy, preferences and navigation checks.
- This guide, read-only status evidence, README and requirements progress update.

## Validation and phase acceptance

Eight new cases verify read-only health/revision and missing files, mode mismatch, API key/URL omission and redacted failures, timezone apply/reset in readonly mode with no HTTP, preference application and invalid-value fallback on Home, missing database with API help retained, configured-but-unauthenticated messaging, and navigation across all six real routes with no implicit HTTP or revision changes.

The full suite passes **478 tests**, with lint, formatting and whitespace checks passing. Tests use temporary databases, injected configuration and captured provider responses; they do not read actual API credentials or mutate working sample/live files. The read-only working-data status evidence is in [the local status report](12_06_settings_result.json). It contains no API credentials or private connection details.

Phase 12 completed the runnable navigation shell and six page contracts. Existing Phase 10 services power CRUD; Phase 11 SQL powers Analytics; Phase 9 imports power saved matches and career data. Missing/partial provider history is still disclosed. A fresh authenticated dashboard refresh has not been performed merely to complete this page, and no complete global leader population is claimed. Public administrative authentication and hosted persistence remain outside this local page milestone.

Concepts learned: trusted configuration versus session preferences, immutable settings replacement, timezone validation, operational diagnostics versus live authentication, secret-safe summaries, service/presentation separation and full-route UI regression checks.

Next phase preview: **Phase 13 — Visualization** will explain and add suitable charts for rankings, trends, player and venue comparisons, with source/sample/coverage labels and documented reasons for each chart. Advance only after the user's next request.
