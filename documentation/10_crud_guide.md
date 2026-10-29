# Phase 10: CRUD implementation completed

CRUD means create, read, update and delete. The services now support those operations for player profiles and batting, bowling and fielding performances. Streamlit forms belong to Phase 12; no dashboard UI is claimed here. Phase 11 analytical questions have not started.

## Implemented files

- `services/players.py`: `PlayerService` provides create, get, list, update, delete, restore and release_override.
- `services/match_stats.py`: `MatchStatsService` provides the same lifecycle for each supported performance kind.
- `services/_crud.py`: shared version checks, timestamps, safe bound writes, ownership rules and transaction error translation.
- `tests/test_player_crud.py` and `tests/test_match_stats_crud.py`: 30 service acceptance checks against isolated temporary databases.

The existing database schema, API importer, repositories and views are reused. No schema migration is required. Player services work with the supported schema 1/2 databases; API-ingestion demonstrations use schema 2.

## How editing works

Read a row, retain its `version`, then pass that version with the edit. A successful content change advances the row version and dataset revision once. An unchanged patch changes neither. A stale version or missing row raises `StaleRecordError`: reload before trying again. The database starts write transactions with `BEGIN IMMEDIATE`, and the update also matches the expected version.

User values are bound parameters. Dynamic table/column identifiers come from fixed internal definitions. Callers cannot patch source IDs, match/team/innings/player identities, ownership, version, timestamps or deletion flags through ordinary edit fields.

Example using the already configured database:

```python
from config import load_settings
from utils.db_connection import Database
from services.players import PlayerService

# These calls change the configured database. Use a separate practice target
# while learning; no demonstration edits were made to your working databases.
database = Database(load_settings())
try:
    players = PlayerService(database)
    created = players.create({"full_name": "Practice Player"})
    edited = players.update(
        created["player_id"], created["version"], {"batting_style": "Left-hand bat"}
    )
    deleted = players.delete(edited["player_id"], edited["version"])
    restored = players.restore(deleted["player_id"], deleted["version"])
finally:
    database.close()
```

## Player validation

Names must be nonblank text. A role ID must identify an existing role. Batting/bowling styles may be unknown (NULL). Two people can have the same name; identity is the local player ID, not name uniqueness. New records are manual and do not fabricate provider identities, career statistics or team memberships.

## Match-stat validation

A performance is identified by kind, innings ID and player ID. `create(kind, innings_id, player_id, match_id, team_id, fields)` requires an active player, an existing innings belonging to the match, and an existing match-player association on the correct team. Batting belongs to the batting team; bowling and fielding belong to the bowling team. Creating a profile alone does not establish a match appearance. Creating matches, innings or match-player associations is outside this CRUD scope.

Allowed editable fields:

| Kind | Fields |
| --- | --- |
| batting | batting_position, runs, balls_faced, fours, sixes, is_dismissed, dismissal_text |
| bowling | legal_balls, runs_conceded, wickets, maidens |
| fielding | catches, stumpings |

Counts must be nonnegative integers, not booleans or decimal counts. Batting positions are 1–11, wickets at most 10, known boundary runs cannot exceed total runs, and known maiden overs cannot exceed legal balls bowled. Validations use the combined existing row and patch, so changing only runs cannot invalidate existing boundaries. NULL clears a field to unknown rather than zero. Bowling input uses integer legal balls; a later form can convert overs with the cricket utility. A duplicate performance or occupied batting position is rejected without replacing another row.

`get` and `list` hide deleted performance rows and performances of deleted players. Administrative `get(..., include_deleted=True)` can inspect retained rows for restoration. These CRUD reads include stored super-over rows; the established analytic views separately exclude super overs from ordinary-innings analysis.

## Deletion, restore and API ownership

Deletion is logical: it sets a tombstone and retains dependent history. Deleting a player hides the player and their joined performance/career results. It does not separately tombstone their performance rows. Restoring that player makes their individually active history visible again. Updating or restoring statistics requires an active player and valid match relationships.

Changing an API-owned record requires `override=True`. The record then becomes an override. Future API imports skip overrides and tombstones. Restoring an overridden record preserves override ownership; it does not silently return control to the API.

`release_override(..., expected_version)` deliberately returns an active override to API control. The next successful eligible refresh may overwrite the local correction. It does not fetch immediately. A deleted override must be restored before release. Manual records cannot be released as invented API records. Later UI forms must make override/release choices visible and obtain intentional delete confirmation before calling the services.

## Failure and access behavior

Invalid inputs, wrong relationships, stale versions, protected ownership and conflicting uniqueness constraints leave data and dataset revision unchanged. An import's existing manual/override/tombstone protections remain in effect. Readonly mode permits reads and rejects every service write at the central transaction boundary. This is local service access control, not a deployed administrative login system.

The services return safe validation/ownership/conflict errors. Database constraint errors are translated without exposing the raw database statement. No physical-delete operation is exposed.

## Validation and learning checkpoint

The full suite passes **218 tests**, including 30 new CRUD tests. Ruff lint, formatting and whitespace checks pass. Tests cover all three statistic kinds, create/read/update/delete/restore, missing and stale records, parameter-bound text, wrong match/team/player associations, duplicate rows, invalid counts, combined-field checks, no-op updates, NULL values, read-only access, player deletion visibility, API override/tombstone persistence and deliberate release followed by API refresh.

No API request was needed for this phase. Tests use temporary copies/targets; the working sample and live datasets were not edited. Files with credentials were not used by these service tests.

M4 and LEARN-10 are complete at the service layer. Product interface requirements remain pending until the Streamlit forms exist. Next: Phase 11 teaches the 25 SQL questions individually, advancing only on NEXT under the adopted mentoring workflow.
