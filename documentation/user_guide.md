# User guide

Start with the [installation guide](environment_setup.md). Check Home for dataset mode, provenance and last import time before interpreting any result.

| Page | Suggested action | Interpretation |
| --- | --- | --- |
| Home | Review counts and open the documentation links | Saved database summary, not API freshness proof |
| Live Matches | Filter status, select a match, inspect every innings | Saved statuses can be old; absent detail remains unknown |
| Top Players | Choose source, exact format and ranking metric | Latest saved careers in that source; not a global leaderboard |
| Analytics | Select a question, inspect SQL/parameters, run and compare its table | Results obey that question's scope and qualification rules |
| Analytics → Visualizations | Explore quarterly trends, consistency and venue comparisons | Missing quarters remain gaps; units and combined-format scopes are labelled |
| CRUD | Load a record before editing; review ownership and delete confirmation | Local administration, version checking and soft deletion |
| Settings | Inspect database health and change display timezone | Session preference only; no credentials displayed |

Custom SQL is available to local operators with enforced read-only restrictions and result/time limits. Public demo visitors cannot edit or run custom SQL. For CRUD practice, use a disposable sample database; do not use provider facts to rehearse destructive changes. Release an API override only when you intend future imports to own that fact again.

## Demonstration sequence

Show the sample label and counts on Home, inspect one innings in Live Matches, compare two sample players in Top Players, run a saved Analytics question and explain its chart, then show Settings health. This sequence needs no HTTP or writes. Keep credentials and private browser panels out of recordings. See the [screenshot plan](screenshots/README.md).

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Missing database | Confirm mode/path; initialize only a new target using the database guide |
| Mode/schema mismatch | Select the correct file; use explicit migration only when needed |
| Empty ranking/chart | Review source, exact format, thresholds and imported coverage |
| Old live score | Inspect import time; explicitly refresh only with quota available |
| Refresh disabled | Confirm local access, live schema 2, provider configuration and cooldown |
| Edit conflict | Reload the latest record and review changes before resubmission |
| SQL rejected/limited | Use supported read-only statements; narrow selected columns/rows |
| Unexpected page error | Return Home/reload; check the safe diagnostic code; an action may already have committed |
| Port already in use | Choose another local port; avoid terminating an unrelated process |
| Docker unavailable | Start its engine; the current Linux image passed build/runtime/restart checks |

Errors deliberately hide private SQL, keys and raw responses. Share safe codes and reproduction steps instead of credentials. [API operations](api_setup.md), [database recovery](database_setup.md) and [deployment](16_deployment.md) provide the operational details.

[Local features versus public demo](live_refresh_and_demo.md) explains refresh permissions and sample-data limits.
