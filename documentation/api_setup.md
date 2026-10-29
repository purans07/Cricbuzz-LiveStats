# API setup and imports

## Selected provider

The reviewed manifest is [cricketapilive v2](../api/contracts/cricketapilive_v2.json), for [the RapidAPI listing](https://rapidapi.com/cricketapilive/api/cricbuzz-cricket). Authenticated capability checks were recorded on 2026-10-22. The listing version is v2 while the verified HTTP routes below contain v1; do not substitute guessed version paths.

| Capability | Route |
| --- | --- |
| Live list | /matches/v1/live |
| Regular scorecard | /mcenter/v1/{matchId}/scard |
| Profile | /stats/v1/player/{playerId} |
| Career formats | /stats/v1/player/{playerId}/career |
| Career batting/bowling | /stats/v1/player/{playerId}/batting and /bowling |
| Series matches | /series/v1/{seriesId} |

The series route has capability evidence but no complete historical backfill workflow. The Hundred hscard route is not the regular scorecard adapter.

## Private configuration

In a private .env, set CRICBUZZ_CONTRACT_FILE to `api/contracts/cricketapilive_v2.json` and CRICBUZZ_API_KEY to your private credential. Do not paste keys into guides, screenshots, request examples or Git. Replace any previously exposed key through the provider account. The API loader uses .env/process environment; it does not consume st.secrets.

The manifest fixes HTTPS host `cricbuzz-cricket.p.rapidapi.com`, x-rapidapi-host, CB-Loc IN and CB-TZ +0530; the private key supplies x-rapidapi-key. Manifest edits require review and matching adapters, not only a URL change.

## Prepare a separate live database

```sh
APP_ACCESS_MODE=local .venv/bin/python -m database.initialize --mode live --database data/runtime/live.db
.venv/bin/python -m database.initialize --mode live --database data/runtime/live.db --check
.venv/bin/python -m api.cli check-config
```

Initialize only if absent. check-config checks configuration readiness without HTTP and does not establish subscription/authentication success. Imports require schema 2 and local operator access.

## Explicit imports

These commands consume provider quota. IDs are provider IDs, not internal database IDs:

```sh
APP_ACCESS_MODE=local .venv/bin/python -m api.cli sync-live --database data/runtime/live.db
APP_ACCESS_MODE=local .venv/bin/python -m api.cli sync-scorecard 147931 --database data/runtime/live.db
APP_ACCESS_MODE=local .venv/bin/python -m api.cli sync-player 8583 --database data/runtime/live.db
```

Player enrichment makes three requests for profile, batting and bowling. The client supports career-format capability separately. Do not repeat requests just to navigate the app. Subscription limits can change; inspect your account before refreshing.

The reviewed policy uses 3-second connection/10-second read timeouts, a 20-second operation budget, 2 MB response cap, one attempt and a 2-second minimum client interval. Dashboard refresh adds a process-local mutex and at least 30-second cooldown/Retry-After handling; it is not an account-wide quota limiter.

Imports normalize source identities, skip advertisements, preserve missing values, use atomic transactions and reject stale/duplicate changes. API-owned operator overrides and tombstones are protected. Refreshing a list does not delete older saved matches absent from that response.

## Coverage and failures

Saved coverage after verification on 2026-10-29 is 87 matches, 199 innings, partial detailed scorecards and three enriched career players. Exact provider format labels remain distinct. No global ranking or complete fielding/history coverage is claimed. See [verification](09_live_verification.md) and [Phase 9 completion](09_api_implementation.md).

If configuration is missing, check variable names and manifest path privately. For authorization/subscription/rate failures, inspect the provider account and wait before retrying. Do not put private responses in logs. Failed import transactions roll back; read the last successful import time before assuming displayed scores are fresh. Tests use injected transports and a default requests guard, not paid calls.

## Additional verified imports (2026-10-29)

```bash
python -m api.cli sync-recent --database data/runtime/live.db
python -m api.cli sync-series 11595 --scope International --database data/runtime/live.db
```

Use `--configured` instead of `--database PATH` to select a configured server backend with DATA_MODE=live. An explicit file path always selects SQLite. These commands use provider quota; browsing saved data does not. See [fresh verification and limits](remaining_requirements_completion.md).
