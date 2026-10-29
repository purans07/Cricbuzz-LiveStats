# Live refresh and public demo

## Two deliberately different modes

| Capability | Trusted local application: main.py | Public sample: cloud_app.py |
| --- | --- | --- |
| Data | Selected sample or saved provider database; configured server backend supported | Fictional sample, initialized only if missing |
| Saved matches/players/charts | Available | Available |
| Saved SQL analyses | 26 | 26 |
| Custom SQL | Restricted readonly interface | Disabled |
| Player and match-stat CRUD | Validated operator forms | Writes disabled |
| Provider list/scorecard refresh | Explicit button, live writable target and private credentials required | Disabled |
| Player enrichment / recent / series imports | Explicit local CLI commands | Not offered |
| API key needed | Only for actual provider requests | No |

## What live means here

Navigating, changing filters, selecting matches and browsing players read committed saved data; they do not trigger background provider calls. A local operator explicitly refreshes a live match list or selected scorecard. The request is normalized and imported atomically; only a successful import reloads the saved view. Failed imports retain old records and show failure. Older records absent from a list response remain stored; their previously live status is not proof they are ongoing now.

RefreshCoordinator serializes requests within one process and enforces at least a 30-second cooldown plus provider Retry-After handling. Client calls have time, size and retry budgets. This is not an account-wide quota governor across multiple processes. There is no continuous polling, push streaming or guaranteed score latency. The brief's real-time requirement is satisfied only under an on-demand refresh interpretation; it is partial under a continuous-live interpretation.

Import time indicates saved freshness, not proof of current scores. Source scopes and missing details remain visible. Top Players uses latest imported career snapshots; it is not a global live leaderboard. Current provider coverage is documented separately with dated evidence.

## Verification

Tests in test_live_matches_page.py, test_api_client.py, test_ingestion.py and test_deployment.py exercise no-request browsing, guarded refreshes, cooldown/failure paths, rollback and public write restrictions. Dated actual authenticated API checks are in api_verification_2026_10_29.json. The walkthrough uses an isolated fictional local dataset to demonstrate CRUD without publishing private data or spending provider quota. Public demo does not claim to demonstrate API refresh or administrative edits.
