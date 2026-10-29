# Phase 5 API analysis

Cricbuzz LiveStats needs a provider contract before live API implementation. You confirmed that no provider has been selected. This phase therefore delivers documentation research, a provisional capability-to-table map and an explicit verification checklist. It does not claim authenticated access, a working endpoint, an observed JSON response, or sufficient historical coverage.

The main finding is that Cricbuzz-branded API listings expose different versions and route conventions. Do not combine a route from one listing with a hostname, credential convention or response parser from another. No paid plan has been selected or purchased.

## 1 Evidence and provider decision

Evidence labels used below:

- **Documented:** visible in provider/platform documentation or its indexed public description; not a successful API test.
- **Proposed:** our adapter, ingestion or database design.
- **Pending:** requires a selected provider/version, authenticated documentation access or a real response.

The RapidAPI Cricbuzz Cricket listing is a candidate for evaluation, not a verified official Cricbuzz-operated service. The public materials inspected do not establish Cricbuzz affiliation. Its indexed pages show v1 and v2 contexts. The v1 page labels a live-match operation; the v2 page describes a scorecard operation with a required match identifier. Direct page opens returned little extractable content, so the indexed descriptions are evidence of documentation only. [Candidate listing](https://rapidapi.com/cricketapilive/api/cricbuzz-cricket), [v1 live operation](https://rapidapi.com/cricketapilive/api/cricbuzz-cricket/playground/matches%2Flive), [v2 scorecard operation](https://rapidapi.com/cricketapilive/api/cricbuzz-cricket/playground/apiendpoint_38fe7ec9-e3ba-4d9a-b938-c6c5836c36ad).

APIDojo also publishes a Cricbuzz reference with named GET operations for players, series and venues. Treat this as a separate contract reference, not proof that its routes work with the RapidAPI candidate above. The names in the next section come from that reference. Its directly opened page required JavaScript; indexed documentation supplied the visible operation descriptions. [APIDojo provider reference](https://apidojo.net/documentations/cricbuzz).

**Proposed next decision:** evaluate the RapidAPI candidate's selected version against the required capabilities. Reject it if scorecards, career batting/bowling or historical match discovery are unavailable on an acceptable plan. A listing's name alone is not enough to choose it. No production base URL is finalized in this phase.

## 2 Available documented operations

These are operation labels, not copy-ready request URLs. GET is documented for each. Resolve the complete gateway URL, parameter location and version from the chosen provider's request example before implementation.

| Reference | Operation label | Documented input or role | Our proposed destination |
| --- | --- | --- | --- |
| RapidAPI v1 | matches/live | No additional parameters shown | Match-list ingestion |
| RapidAPI v2 | match-details/get-scorecard | Required matchId path parameter | Innings and performance ingestion |
| APIDojo | players/search | plrN search term | Player identity discovery |
| APIDojo | players/get-info | playerId | Player profile |
| APIDojo | players/get-batting | playerId | Career batting snapshot |
| APIDojo | players/get-bowling | playerId | Career bowling snapshot |
| APIDojo | players/get-career | playerId | Career/format coverage inspection |
| APIDojo | series/get-squads | seriesId | Squad candidate discovery |
| APIDojo | series/get-seasons | seriesId | Historical discovery |
| APIDojo | series/get-stats | seriesId, statsType | Series-scoped leaderboard |
| APIDojo | venues/get-info | venueId | Venue enrichment |
| APIDojo | venues/get-matches | venueId | Match discovery |

Table sources: the two RapidAPI operation pages and the APIDojo reference linked above. Database destinations are our design, not a provider guarantee. The inventory covers project-relevant operations visible during research; it is not an exhaustive list of a selected subscription's available endpoints.

A series leaderboard is not a career leaderboard. Do not store series-scoped results in career_stats_snapshots, whose scope constraint is career. Until a separate aggregate model is justified, display series leaderboards directly as cached provider results with their series scope visible.

Other required capabilities—recent/completed matches, match metadata and toss/results, series archives and details, team lists and confirmed playing XI, fielding totals, and global statistics—remain pending exact operation verification. Do not infer a supported route merely from a URL pattern found in another project.

## 3 Methods, authentication and request headers

The application consumes GET requests. Local CRUD changes our SQL database; it does not POST, PUT or DELETE upstream cricket records.

For a provider accessed through RapidAPI, the platform documents X-RapidAPI-Key and X-RapidAPI-Host on requests. The key identifies the RapidAPI application; the host identifies the API. This does not establish the values for an unselected listing. [RapidAPI authentication](https://docs.rapidapi.com/v2/docs/configuring-api-authentication).

Proposed request contract, deliberately without a real host or secret:

```text
GET <selected endpoint and version>
X-RapidAPI-Key: <loaded server-side from secrets>
X-RapidAPI-Host: <copied from the selected provider request example>
Accept: application/json
```

Accept is our requested response format, not a promise the server will honor it. A GET request has no JSON body unless the actual provider contract unusually requires one. Validate the response content type and parse result. Add no guessed Bearer token or provider-specific header.

The server-side client loads credentials from external configuration, uses an allowlisted HTTPS base URL and sends requests through requests.Session. Neither page JavaScript nor saved JSON fixtures contain keys. Keep request logs free of secret headers and credential-bearing URLs.

## 4 Rate limits, quotas and refresh budget

The selected listing's pricing page could not be retrieved reliably during this research. No numeric quota, cost, overage policy or refresh interval is verified. A free-plan example from another API is not evidence of this API's allowance.

RapidAPI documents plan-usage headers such as x-ratelimit-requests-limit, x-ratelimit-requests-remaining and x-ratelimit-requests-reset, depending on configuration. Its response-header documentation also identifies x-rapidapi-mock-response, which can distinguish a gateway mock from a provider response. [Platform response headers](https://docs.rapidapi.com/docs/response-headers).

Request-rate limits and billing-period quotas are different. A low request rate can still exhaust a monthly allowance. Record the chosen plan's hard limit/overages, reset window, per-endpoint cost if applicable and available response headers before enabling timed refresh. [Rate versus quota header distinctions](https://docs.rapidapi.com/v1.0/docs/response-headers).

Proposed planning formula:

```text
calls = list refreshes
      + scorecard refreshes across selected matches
      + player/profile/stat lookups
      + history and venue lookups
      + retries
```

For illustration only, a list and one scorecard fetched every minute for an hour consume about 120 calls before enrichment or retries. This is arithmetic, not an approved refresh policy. Start with explicit refresh and reuse cached snapshots. Set minimum intervals only after the plan is verified. If a throttle delay exceeds the interaction budget, return a stale snapshot and a next-allowed-refresh message instead of blocking the interface.

## 5 JSON responses and adapter contract

No authenticated provider payload has been captured. Exact JSON paths, wrapper names, arrays versus maps, timestamp units and enum values are pending. The following example is **synthetic normalized application data**, not a response copied from any provider:

```json
{
  "source": "unselected-provider",
  "capability": "match_scorecard",
  "fetched_at": "2026-10-21T00:00:00Z",
  "completeness": "partial",
  "match": {
    "external_id": "fixture-match-1",
    "status": "live"
  },
  "innings": [{
    "innings_number": 1,
    "batting_team_external_id": "fixture-team-a",
    "bowling_team_external_id": "fixture-team-b",
    "legal_balls": 26
  }]
}
```

The example intentionally lacks enough records for insertion. A real import needs resolved teams, match format, player identities and required relationships. Adapter output must carry field-presence information or equivalent patch semantics: omitted values, explicit unknown values and explicit zero values must not collapse into the same update action.

Parsing rules to implement in Phase 9:

1. Confirm HTTP outcome before accepting the response as successful data.
2. Parse JSON safely and validate the selected provider's actual response shape.
3. Skip recognized non-record wrappers only after observing and documenting them; reject unknown structures rather than silently returning an empty dataset.
4. Preserve external IDs consistently as strings. Resolve them through source_id + external_id, never player names alone.
5. Normalize dates after verifying seconds versus milliseconds. Preserve unknown completion times rather than substituting a scheduled end time.
6. Convert overs as a cricket notation: 4.2 means 26 legal balls; reject impossible ball suffixes.
7. Resolve role/format/status enums explicitly; preserve original status wording for unusual results.
8. Validate enough related records for the chosen transactional import unit. Mark incomplete coverage honestly.
9. Record whether the result is a provider response, documentation example, synthetic fixture or gateway mock. A mock must not count as a successful live integration test.

## 6 Capability to table and field mapping

This is a semantic mapping to our schema. It becomes a verified field-level mapping only after actual provider keys and sample values are recorded.

| Capability | Required semantic fields | Destination | Important validation |
| --- | --- | --- | --- |
| Source/fetch metadata | Provider identity, fetch time, upstream time if supplied, capability, completeness | sources, import_batches | Correct provider/version; committed only after successful transaction |
| Match listing/details | Match ID, description, format, start time, state, teams, venue, series | matches, match_teams, teams, formats, venues, series | Resolve two participant slots; listing is not a complete scorecard |
| Toss/result details | Toss team/decision, winning team, typed margin and completion time | matches | Winner/toss belongs to match; keep runs and wickets separate |
| Scorecard innings | Match ID, innings order, batting/bowling team, score, wickets, overs | innings | Correct match teams; distinguish super overs |
| Batting lines | Player ID, position, runs, balls, boundaries, dismissal status | match_players, batting_performances | Batting team FK; a missing dismissal is not automatically not-out |
| Bowling lines | Player ID, overs, conceded runs, wickets, maidens | match_players, bowling_performances | Bowling team FK; integer legal balls |
| Fielding lines/events | Fielder identity, catches and stumpings | match_players, fielding_performances | Coverage unverified; do not invent zero catches from absent data |
| Player search/profile | Player ID, name, role, batting/bowling style | players, playing_roles | Names are not unique identities |
| Representation evidence | Player, team, country and observed/effective dates | teams, countries, player_team_memberships | Squad membership alone is not a confirmed match appearance |
| Confirmed lineup | Match, player, team and confirmation state | match_players | confirmed_xi only with explicit evidence; scorecard observation uses observed |
| Career batting/bowling | Player, format, career totals/ratios and snapshot scope | career_stats_snapshots | Career only; aligned scopes and known denominators |
| Series metadata | ID, name, dates, host countries, formats, planned count | series, series_hosts, series_formats | Hosts and planned count must be supplied or known, not guessed from venues/current fixtures |
| Venue information | ID, name, city, country, capacity | venues, countries | Capacity may be absent or formatted text; store unknown rather than zero |
| Dataset mode/revision | Local data mode and successful-change count | dataset_state | Application metadata, not fetched upstream |

Performance rows use the match, innings and resolved player identity as their natural import keys. No upstream performance ID is required. API imports must skip override/manual rows and tombstones under the Phase 4 ownership policy. An older or partial snapshot must not erase newer known data.

### Schema gaps identified during analysis

- The existing schema cannot store series leaderboards as career snapshots. Keep their output explicitly series-scoped; a persisted leaderboard table would be a later reviewed addition.
- Batting and bowling may be separate requests while a career snapshot row holds both. Normalize them into a shared logical batch only when scopes align, with actual sub-request timestamps retained in sanitized fixture metadata. Do not pretend simultaneous retrieval or completeness. A request-level provenance table may be needed if precise production lineage becomes mandatory.
- Ordinary profile endpoints may list current teams without dated membership evidence; use an observation-date interval as documented in Phase 4, not invented historical membership.
- The schema can store fielding counts, but no tested extraction source exists yet. Q21 real-data completeness remains unresolved.

No schema changes are made on the basis of untested response assumptions.

## 7 Historical coverage and SQL readiness

Every row below is pending live coverage verification. A documented capability is not evidence that sufficient history is available under an acceptable plan.

| Questions | Coverage required | Current evidence gap |
| --- | --- | --- |
| Q01, Q06 | Representative player population, roles and representation | Search/trending lists may not enumerate all eligible players |
| Q02, Q05, Q10 | Recent/completed matches with dated results | Date span, stable ordering and total completeness unknown |
| Q03, Q07, Q09, Q11 | Career stats by format, dismissals/averages and highest scores | Exact career fields and format scope untested |
| Q04 | Capacities above 50,000 and location | Venue capacity availability untested |
| Q08 | Series beginning in 2024, hosts, formats and planned counts | Archive access and planned-count metadata untested |
| Q12, Q17, Q22 | Team countries, venue countries, toss/results, actual innings order; five head-to-head games over three years for Q22 | Country consistency, toss fields and historical depth unknown |
| Q13, Q24 | Ordered batting positions in full innings; five eligible pair occurrences for Q24 | Position semantics and scorecard history untested |
| Q14, Q18 | Bowling history meeting venue and appearance/over thresholds | Complete historical bowling lines untested |
| Q15, Q16, Q19, Q20 | Typed margins, participation and batting history, including since 2020/2022 and 20-match eligibility | History span, XI coverage and dismissal status unknown |
| Q21 | Aligned batting, bowling and fielding data per format | Catches/stumpings and denominator availability unresolved |
| Q23 | Last ten batting performances with reliable ordering | A career endpoint alone cannot supply the sequence |
| Q25 | At least six eligible quarters, minimum three matches per quarter | Multi-year innings history and retrieval budget unknown |

Use clearly labeled synthetic fixtures later to prove SQL boundary behavior. Such fixtures do not resolve live coverage gaps. Keep real-data query completeness separate from query correctness.

## 8 Pagination and historical discovery

The inspected v1 live-operation description shows no extra parameters; that does not prove every endpoint is unpaginated. No cursor, page size or complete-history guarantee has been verified for the candidate contract.

For each selected operation record: pagination type, parameter names, continuation field, ordering, page-size bounds, date filters, retention window and explicit termination behavior. If pagination exists, stop on the documented end condition and guard repeated cursors/IDs. Do not invent page=2 or assume an empty page is always the only termination signal.

Series and venue discovery may require traversing identifiers rather than requesting chronological pages. A recent-match list is not a historical archive. Backfill budgeting must account for discovery, one or more detail requests per match, enrichment and retries. Build an inventory of expected IDs and fetched IDs so partial coverage is measurable.

## 9 Error handling and safe ingestion

Proposed client behavior, to be adjusted against the chosen provider's actual error contract:

| Condition | Behavior |
| --- | --- |
| Invalid input or missing identifier | Reject locally where possible; do not repeatedly retry |
| Authentication/subscription rejection | Report configuration/access issue; do not retry unchanged credentials |
| Not found | Treat the requested entity as unavailable; do not delete stored history automatically |
| Rate limited | Respect documented retry guidance, budget and UI time limit; preserve stale data |
| Timeout or transient server failure | Bounded retry with backoff and jitter; never retry forever |
| Redirect | Validate expected gateway behavior and avoid forwarding credentials to an unexpected host |
| No-content response | Apply endpoint-specific meaning; do not unconditionally parse as JSON |
| HTTP success with an error object or HTML | Reject as invalid data, retain prior snapshot and log safe diagnostics |
| Partial record or missing FK dependency | Reject or defer the import unit with an explicit reason; no orphan inserts |

HTTP status alone is not a complete provider error model. Confirm any unusual status semantics in the selected provider's documentation and fixtures. API calls happen before opening the write transaction. Persist dependency records in order, use repeatable keys, update batch status/revision on commit, and roll back failed imports.

## 10 Provider acceptance and authenticated verification checklist

These checks remain open. They are the prerequisites for claiming the live contract is implementation-ready, not permission to purchase a subscription.

- [ ] Choose one provider listing and one API version.
- [ ] Confirm complete HTTPS base URL and host header from that version's request example.
- [ ] Review plan cost, hard limits/overages, request-rate limits and allowed project use.
- [ ] Configure the API key privately through environment/deployment secrets; never paste it into chat or commit it.
- [ ] Obtain a real successful match-list response, record safe status and quota metadata.
- [ ] Obtain a scorecard for an ID discovered from that provider's list, including a multi-innings example where available.
- [ ] Inspect match metadata, toss, results, venue and confirmed-XI capability.
- [ ] Verify player search/profile and career batting/bowling output by format.
- [ ] Verify career fielding data or document its absence.
- [ ] Verify series discovery, archive depth, hosts and planned counts.
- [ ] Verify venue country/capacity and team classification.
- [ ] Confirm exact JSON paths, units, null conventions, enums and pagination per operation.
- [ ] Save sanitized fixtures with provider/version/capability and capture time, explicitly distinguishing live responses from mocks.
- [ ] Estimate calls for the required historical dataset and select a refresh policy within budget.
- [ ] Update the field map and schema only from verified response evidence.

No credentials were inspected, no authenticated calls were made, and no numeric plan allowance is assumed. The product can continue to be structured around the adapter boundary; live implementation must not hardcode these provisional labels as a verified contract.

## Phase completion

**What we completed:** researched project-relevant provider documentation, distinguished API versions, explained GET/authentication/headers and quota concepts, mapped capabilities to all 21 schema tables, defined a normalized JSON contract, analyzed pagination and history gaps, and prepared provider acceptance checks.

**File created:** documentation/05_api_analysis.md. The Phase 2 checklist records documentation analysis separately from pending authenticated verification.

**Concepts learned:** operation labels versus request paths, provider/version contracts, authentication headers, quotas versus request rates, source JSON versus normalized records, scope-aware statistics and evidence-based coverage.

**Common mistakes to avoid:** mixing providers, copying example keys, assuming a free allowance, treating series totals as career totals, inventing pagination, marking mocks as live data, and promising complete historical analytics from a recent-match list.

**Next phase preview:** Phase 6 creates and explains the project folder skeleton, keeping the provider adapter configurable. It can proceed with a provider-neutral structure; the open verification checks must be resolved before production live ingestion. The adopted mentoring prompt requires confirmation before moving phases.
