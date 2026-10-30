# Public API-backed deployment

cloud_app.py defaults to verified provider records when PUBLIC_DATA_MODE is not set. PUBLIC_DATA_MODE=sample explicitly keeps the fictional demo. Public API-backed mode creates a separate public-provider.db from normalized, versioned sporting records, retaining source and import timestamps. It never copies a private runtime database or exposes a provider key. Existing sample and operator databases remain separate.

The website is read-only. Its users cannot make API calls, edit records or run custom SQL. Startup validates/imports only bundled sporting snapshots; it makes no provider request. GitHub Actions runs refresh-provider.yml daily at 05:17 UTC (10:47 IST). Each run makes one live-list call and at most two full-scorecard calls, validates normalization and relational import in an isolated database, then commits only the normalized latest-match snapshot. Failed requests preserve the published file. Workflow concurrency prevents overlapping jobs. Schedules can be delayed; repeated manual runs consume additional requests. Daily match-list updates are not ball-by-ball live scoring.

CRICBUZZ_API_KEY is held in a GitHub repository Actions secret, not Streamlit secrets or Git. The reviewed provider contract fixes the route. The last known account window limit was 200; at most 84–93 scheduled requests/month leaves capacity for explicit operator enrichment. This is a request count, not a billing guarantee. Completed detailed scorecards are cached and missing eligible matches are filled in gradually; it does not refresh every player's career; imported coverage is labelled partial. Raw captures, request headers and working database files are excluded from publication.

The initial release includes verified recent/series matches and two players' career snapshots. Those original fetch timestamps are preserved. The daily feed subsequently updates match lists/innings summaries; the latest list does not delete older matches. Career and detailed-scorecard enrichment remain reviewed operator import work. No global leaderboard, exhaustive history or continuous freshness is claimed.

## Acceptance

The repaired GitHub refresh run 40996331942 succeeded. Full local regression: 597 passed, 64 opt-in server checks skipped; lint and formatting passed. The first strict import rejected a national team appearing in a league wrapper; regression coverage now preserves international identity while rejecting conflicting names. The verified real-data release initially contains 76 matches and two enriched players; exact counts may increase as subsequent responses are merged.

## Detailed scorecards

The daily job now selects up to two scorecards: ongoing matches from the latest list first, then recent completed matches missing saved detail. Completed scorecards with both batting and bowling records are reused. Unsupported responses retain old files and do not erase data; authentication/rate-limit failures stop further detail requests. Maximum cost is three requests per daily run, with additional manually dispatched runs consuming extra quota. Bangladesh vs Scotland (provider ID 175081) was verified and imported with ten batting and ten bowling rows across two innings. Not every stored match has been backfilled yet.
