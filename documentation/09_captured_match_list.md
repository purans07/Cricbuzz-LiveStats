# Captured Cricbuzz v2 match-list integration

The user selected RapidAPI cricketapilive/cricbuzz-cricket, v2, and supplied a matches/live response after a screenshot showed HTTP 200. The pricing screenshot showed Basic at USD 0/month with 200 requests/month, a hard request limit, a separate bandwidth allowance/fee and 1,000 requests/hour. These are user-visible observations, not a fresh verification of billing or account terms.

The supplied response body is retained in tests/fixtures/cricbuzz_v2_live_user_capture.json. It contains no request headers or API key. The user subsequently supplied the exact live-list transport URL and X-RapidAPI-Host. Response headers and local authenticated verification remain pending. No local credentialed request was made.

## Observed structure and implementation

api/cricbuzz_v2.py maps typeMatches → seriesMatches → seriesAdWrapper → matches → matchInfo and matchScore. It skips the observed ad wrapper and rejects unknown wrapper structures rather than silently dropping them.

The captured body yields:

- Nine matches, including two marked Complete inside the live list.
- Seven series, 18 teams, nine venues and 18 innings summaries.
- Millisecond match/series timestamps and a seconds-based responseLastUpdated value.
- Follow-on innings in which the same team bats in innings two and three.

The adapter creates normalized series, formats, teams, venues, matches, match participants and innings. It does not invent player performances, playing XI, capacities, venue countries, structured toss/winner data or actual completion timestamps. The scheduled endDate is not used as completed_at. Status text remains available for display until structured result details arrive.

International TEST/ODI buckets retain those format codes. Provider T20 is not promoted automatically to official T20I; other buckets use separate codes such as INTERNATIONAL_T20, LEAGUE_T20 and DOMESTIC_TEST. Team classification follows the supplied bucket and needs enrichment for authoritative international-team analytics, especially where the provider groups international-looking competitions under Domestic. Country and venue capacity stay unknown.

The body uses overs ending in .6. The adapter has an explicit provisional provider rule that treats O.6 as the completed next over: 53.6 becomes 324 legal balls. Other examples include 127.1 → 763. The strict manual-input validator still rejects .6. Cross-check this provider interpretation against detailed scorecards before relying on it for final bowling analytics; the original raw values remain in the captured fixture.

## Verification

The full suite now passes **159 tests**. New checks cover the captured counts, ad skipping, state handling, timestamp units, follow-on order, format separation, missing-data preservation, malformed wrappers/overs, duplicates and a transactional temporary-database import. Exact reimport is a no-op.

The captured-response import runs only in a temporary test database, which is discarded. Neither the working Phase 8 sample nor the synthetic API practice file was changed. Tests do not consume the user's monthly request allowance.

## Still needed

1. Live-list URL and host received and configured in api/contracts/cricketapilive_v2.json.
2. A scorecard response for a matchId returned by this list.
3. Player/career and series response contracts needed by the remaining Phase 9 deliverables.
4. Private credential setup and controlled local authenticated verification.

This completes the observed match-list mapping, not the entire API milestone. The selected provider is now known; transport and additional JSON contracts remain open.

## Confirmed transport update

The confirmed URL is https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live and the host header is cricbuzz-cricket.p.rapidapi.com. The UI version remains v2; the literal /v1/ segment is retained because it comes from the actual supplied request, not from a guessed UI-to-URL conversion.

The reviewed manifest enables only live_matches. Initial requests allow one attempt to conserve the observed Basic quota; read timeout is ten seconds, informed by the playground's approximately 5.3-second response. These are local settings, not latency guarantees. Other operations remain unconfigured.

The user also exposed a credential in chat. It was not saved, repeated, or used. A private ignored .env was created with an empty key field for a regenerated credential. No new network call was made. Local verification is pending that private replacement.
