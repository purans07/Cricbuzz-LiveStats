# Phase 9 Validation report

Verification date: 21 October 2026 (Asia/Kolkata).

## Current implementation checks

- Combined pytest result: **136 passed**, no failures in the final run.
- Ruff lint and formatting: passed.
- Python: 3.13.5; SQLite: 3.50.2.
- Dependencies unchanged from the checked Phase 8 lock.
- No authenticated provider request, subscription purchase or deployment occurred.

Transport checks use injected sessions/responses, including successful JSON, timeout/retry, authentication rejection, not-found/redirect/non-JSON responses, size limits, quota/mock metadata, rate-limit cooldown and explicit pagination termination/repeated-cursor/limit errors. They make no network requests.

Normalized-ingestion checks cover schema rejection, typed references, source provenance, replay idempotency, freshness, omitted/unknown preservation, locked manual edits and tombstones, wrong-team/missing-reference/overlapping-membership rollback, mode separation, result ordering and unconfigured/mismatched/mock service preconditions.

Migration checks create temporary schema-1 databases, verify a logically equivalent original backup and preserved data/revision, reject existing backup overwrite and wrong/unsupported modes, and confirm repeat migration is a no-op. They never migrate the working Phase 8 sample.

## Separate synthetic practice round trip

Commands already run:

```sh
.venv/bin/python -m database.initialize --database data/runtime/api_practice.db
.venv/bin/python -m api.cli import-fixture tests/fixtures/normalized_match.json --database data/runtime/api_practice.db
.venv/bin/python -m api.cli import-fixture tests/fixtures/normalized_match.json --database data/runtime/api_practice.db
```

First outcome: committed batch 1, 27 entity records inserted. Second outcome: duplicate batch 1, zero insert/update changes. No HTTP request was issued by these commands. The input is authored synthetic normalized data, not a captured API response.

Practice inspection:

```json
{
  "mode": "sample",
  "revision": 1,
  "tables": 21,
  "views": 6,
  "indexes": 19,
  "players": 2,
  "matches": 1,
  "innings": 2,
  "career_stats_snapshots": 2,
  "foreign_keys": 1,
  "integrity": "ok"
}
```

## Preserved working sample

Read-only inspection confirms its original baseline:

```json
{
  "mode": "sample",
  "revision": 1,
  "tables": 21,
  "views": 6,
  "indexes": 18,
  "players": 12,
  "matches": 72,
  "innings": 192,
  "career_stats_snapshots": 72,
  "foreign_keys": 1,
  "integrity": "ok"
}
```

The existing working sample remains schema 1 with 18 indexes. Fresh/practice schema 2 adds the snapshot uniqueness index, producing 19 indexes without changing table/view counts. Its migration is explicit, additive and backup-protected.

## Live verification remains pending

The configuration check exited with an actionable missing-provider-manifest message. No selected provider/version, active endpoint contract or private key was used to obtain a real response. The vendor JSON adapter is not implemented. Provider plan limits, actual response fields and historical/fielding coverage remain unknown.

Therefore these results prove provider-neutral transport and normalized persistence behavior only. They do not complete M3 or the live API requirements, and do not authorize moving silently to Phase 10.
