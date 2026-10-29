# Future improvements

| Priority | Improvement | Acceptance needed |
| --- | --- | --- |
| 1 | Complete deployment runtime acceptance | Start Docker, build image, verify health/pages/restart persistence and readonly behavior; document results before claiming hosting |
| Complete (2026-10-29) | Sample screenshots and silent walkthrough | See screenshots/README.md and demo/README.md; broader narrated/provider demonstration can follow |
| 1 | Broaden provider history and careers | Quota-aware backfill, multiple players/formats, deduplication and reconciliation against source samples |
| 1 | Improve data completeness | Fielding, winners/toss, participation and missing geography with explicit unknowns and coverage reporting |
| 2 | Public operator authentication | Identity, authorization, secret storage and audited write controls before exposing administration |
| 2 | Durable hosted operations | Restore drills, retention, monitoring, persistent volume choice and concurrency testing |
| 2 | Additional server deployments | PostgreSQL/MySQL support is implemented and locally accepted; expand tested versions, hosted TLS and backup/restore drills |
| 2 | Central quota coordination | Account-wide budgets and cross-process cooldowns before scaling refresh workers |
| 3 | Richer cricket modelling | Verified ball-by-ball events and actual partnerships; adjacent batting positions alone are not partnerships |
| 3 | Advanced analysis | Larger representative history, uncertainty reporting and evaluated models before predictive claims |
| 3 | Continuous verification | CI, coverage measurement, accessibility checks and additional browser/platform acceptance |

The existing six pages, charts, restricted SQL, validated CRUD, safe errors and mocked tests are implemented features. Future work should preserve source ownership, soft deletions, exact format labels and the distinction between fictional fixtures and provider facts. No item here authorizes a paid service or public release.
