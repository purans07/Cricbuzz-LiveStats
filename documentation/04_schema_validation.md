# Phase 4 Schema validation

Validated sql/schema.sql using Python sqlite3 against an isolated in-memory database.

- SQLite runtime: 3.50.2
- Tables created: 21
- Explicit indexes created: 18
- Checks passed: 25 of 25
- Persistent application databases created: none
- Test data: synthetic fixture identities only

| Check | Result |
| --- | --- |
| Schema loads with foreign keys enabled | PASS |
| Circular match/team insertion and valid winner update | PASS |
| Valid batting record | PASS |
| Valid bowling record with 26 legal balls | PASS |
| Valid fielding record | PASS |
| Reject third match team | PASS |
| Reject nonparticipant winner | PASS |
| Reject batting for wrong team | PASS |
| Reject bowler from batting team | PASS |
| Reject fielder from batting team | PASS |
| Reject absent match player | PASS |
| Reject negative runs | PASS |
| Reject unmatched margin unit | PASS |
| Reject tie with winner | PASS |
| Restrict physical player deletion | PASS |
| Reject duplicate provider identity | PASS |
| Reject incomplete provider identity | PASS |
| Reject API performance without batch | PASS |
| Allow persistent override tombstone | PASS |
| Store one career snapshot | PASS |
| Reject duplicate career snapshot grain | PASS |
| Initialize dataset state | PASS |
| Reject extra dataset state row | PASS |
| Rollback restores previous values | PASS |
| Final foreign-key and integrity checks | PASS |

This validates DDL execution and selected integrity rules, not provider integration, SQL analytics correctness, service ownership enforcement, authorization, or PostgreSQL/MySQL compatibility. An override tombstone can be stored; the importer that respects it does not exist yet. The fixture is discarded when the connection closes.
