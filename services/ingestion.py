"""Transactional, source-scoped imports of validated normalized snapshots."""

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from api.adapter import Snapshot
from api.client import APIError
from models.records import validate_record
from utils.db_connection import generated_id, schema_version

ENTITY_KEYS = {
    "countries": ("name",),
    "formats": ("code",),
    "playing_roles": ("name",),
    **{
        name: ("source_id", "external_id")
        for name in ("teams", "venues", "series", "players", "matches")
    },
    "series_hosts": ("series_id", "country_id"),
    "series_formats": ("series_id", "format_id"),
    "player_team_memberships": ("player_id", "team_id", "valid_from"),
    "match_teams": ("match_id", "team_id"),
    "match_players": ("match_id", "player_id"),
    "innings": ("match_id", "innings_number"),
    **{
        name: ("innings_id", "player_id")
        for name in (
            "batting_performances",
            "bowling_performances",
            "fielding_performances",
        )
    },
    "career_stats_snapshots": ("player_id", "format_id", "batch_id"),
}
PRIMARY_IDS = {
    "countries": "country_id",
    "formats": "format_id",
    "playing_roles": "role_id",
    "teams": "team_id",
    "venues": "venue_id",
    "series": "series_id",
    "players": "player_id",
    "matches": "match_id",
    "innings": "innings_id",
}
REFERENCE_TARGETS = {
    "country_id": "countries",
    "format_id": "formats",
    "role_id": "playing_roles",
    "team_id": "teams",
    "batting_team_id": "teams",
    "bowling_team_id": "teams",
    "winner_team_id": "teams",
    "toss_winner_id": "teams",
    "venue_id": "venues",
    "series_id": "series",
    "player_id": "players",
    "match_id": "matches",
    "innings_id": "innings",
}
OWNED = {
    "players",
    "batting_performances",
    "bowling_performances",
    "fielding_performances",
}
RESULT_FIELDS = {
    "winner_team_id",
    "toss_winner_id",
    "toss_decision",
    "result_type",
    "margin_value",
    "margin_unit",
}


@dataclass(frozen=True)
class ImportResult:
    """Safe import outcome and committed batch identity."""

    status: str
    batch_id: int | None
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class IngestionService:
    """Import complete units outside any HTTP request or vendor-specific parser."""

    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    @staticmethod
    def _find(connection, table, fields):
        """Look up a row through trusted identifiers and bound key values."""
        clauses = " AND ".join(f'"{key}" = :{key}' for key in fields)
        return (
            connection.execute(text(f'SELECT * FROM "{table}" WHERE {clauses}'), fields)
            .mappings()
            .first()
        )

    def _reference(self, connection, ref, source_id, expected):
        """Resolve a source-scoped dependent identity rather than guessing a local ID."""
        if ref.get("table") != expected:
            raise ValueError("Reference targets the wrong entity type.")
        if expected in {"countries", "playing_roles"}:
            fields = {"name": ref["name"]}
        elif expected == "formats":
            fields = {"code": ref["code"]}
        elif expected == "innings":
            match = self._find(
                connection,
                "matches",
                {"source_id": source_id, "external_id": ref["match_external_id"]},
            )
            if match is None:
                raise ValueError("Referenced match is missing.")
            fields = {
                "match_id": match["match_id"],
                "innings_number": ref["innings_number"],
            }
        else:
            fields = {"source_id": source_id, "external_id": ref["external_id"]}
        row = self._find(connection, expected, fields)
        if row is None:
            raise ValueError("Snapshot references a missing dependent record.")
        return row[PRIMARY_IDS[expected]]

    def _clean(self, connection, table, row, source_id, columns):
        """Resolve source-scoped foreign references and validate writable record fields."""
        resolved = {}
        for key, value in row.items():
            if isinstance(value, dict):
                expected = REFERENCE_TARGETS.get(key)
                if expected is None:
                    raise ValueError("Unknown reference column.")
                value = self._reference(connection, value, source_id, expected)
            resolved[key] = value
        return validate_record(resolved, columns)

    @staticmethod
    def _stamp(connection, batch_id):
        """Read the committed upstream/fetch timestamp for an import batch."""
        if batch_id is None:
            return None
        row = connection.execute(
            text(
                "SELECT COALESCE(upstream_updated_at,fetched_at) FROM import_batches WHERE batch_id=:batch"
            ),
            {"batch": batch_id},
        ).first()
        return row[0] if row else None

    def ingest(self, snapshot: Snapshot) -> ImportResult:
        """Commit one normalized unit, or leave all its data and revision unchanged."""
        expected_mode = "sample" if snapshot.origin == "synthetic" else "live"
        if self.database.settings.data_mode != expected_mode:
            raise APIError(
                "mode", "Snapshot origin does not match the database dataset mode."
            )
        if self.database.settings.access_mode != "local":
            raise APIError("access", "Import requires local operator access.")
        try:
            with self.database.transaction(write=True) as connection:
                if schema_version(connection) != 2:
                    raise APIError(
                        "schema", "API ingestion requires explicit schema-2 migration."
                    )
                source = self._find(
                    connection, "sources", {"name": snapshot.source_name}
                )
                kind = "sample" if expected_mode == "sample" else "api"
                if source is None:
                    source_id = connection.execute(
                        text("INSERT INTO sources(name,kind) VALUES (:name,:kind)"),
                        {"name": snapshot.source_name, "kind": kind},
                    )
                    source_id = generated_id(connection, source_id, "sources")
                else:
                    if source["kind"] != kind:
                        raise ValueError("Source kind mismatch.")
                    source_id = source["source_id"]
                prior = self._find(
                    connection,
                    "import_batches",
                    {"source_id": source_id, "snapshot_key": snapshot.digest},
                )
                if prior is not None and prior["status"] == "committed":
                    return ImportResult("duplicate", prior["batch_id"])
                effective_time = snapshot.upstream_updated_at or snapshot.fetched_at
                newer = connection.execute(
                    text(
                        "SELECT batch_id FROM import_batches WHERE source_id=:source "
                        "AND capability=:cap AND resource_key=:resource AND status='committed' "
                        "AND COALESCE(upstream_updated_at,fetched_at)>:stamp LIMIT 1"
                    ),
                    {
                        "source": source_id,
                        "cap": snapshot.capability,
                        "resource": snapshot.resource_key,
                        "stamp": effective_time,
                    },
                ).first()
                if newer:
                    return ImportResult("stale", newer[0])
                batch_id = connection.execute(
                    text(
                        "INSERT INTO import_batches(source_id,capability,resource_key,snapshot_key,"
                        "fetched_at,upstream_updated_at,completeness,status) "
                        "VALUES (:source,:cap,:resource,:digest,:fetched,:upstream,:complete,'pending')"
                    ),
                    {
                        "source": source_id,
                        "cap": snapshot.capability,
                        "resource": snapshot.resource_key,
                        "digest": snapshot.digest,
                        "fetched": snapshot.fetched_at,
                        "upstream": snapshot.upstream_updated_at,
                        "complete": snapshot.completeness,
                    },
                )
                batch_id = generated_id(connection, batch_id, "import_batches")
                inserted = updated = skipped = 0
                deferred, touched_matches = [], set()
                inspector = inspect(connection)
                for group in snapshot.groups:
                    table = group["table"]
                    columns = {
                        column["name"]: str(column["type"])
                        for column in inspector.get_columns(table)
                    }
                    for original in group["rows"]:
                        row = self._clean(
                            connection, table, original, source_id, columns
                        )
                        if table in {"teams", "venues", "series", "players", "matches"}:
                            row["source_id"] = source_id
                        if "last_batch_id" in columns:
                            row["last_batch_id"] = batch_id
                        if table == "career_stats_snapshots":
                            row["batch_id"] = batch_id
                        if "updated_at" in columns:
                            row["updated_at"] = snapshot.fetched_at
                        key_names = ENTITY_KEYS[table]
                        if any(key not in row or row[key] is None for key in key_names):
                            raise ValueError(
                                "Snapshot lacks a required record identity."
                            )
                        key = {name: row[name] for name in key_names}
                        current = self._find(connection, table, key)
                        if (
                            current
                            and table in OWNED
                            and (current["ownership"] != "api" or current["is_deleted"])
                        ):
                            skipped += 1
                            continue
                        if current and "last_batch_id" in current:
                            current_stamp = self._stamp(
                                connection, current["last_batch_id"]
                            )
                            if current_stamp and current_stamp > effective_time:
                                skipped += 1
                                continue
                        if current and table in {
                            "countries",
                            "formats",
                            "playing_roles",
                        }:
                            if any(
                                value is not None and current[name] != value
                                for name, value in row.items()
                            ):
                                raise ValueError(
                                    "Conflicting global reference definition."
                                )
                            skipped += 1
                            continue
                        if (
                            current
                            and table == "match_players"
                            and current["team_id"] != row["team_id"]
                        ):
                            raise ValueError(
                                "Player cannot change teams within a match."
                            )
                        if table == "player_team_memberships" and current is None:
                            overlap = connection.execute(
                                text(
                                    "SELECT 1 FROM player_team_memberships WHERE player_id=:player "
                                    "AND team_id=:team AND valid_from<=:end "
                                    "AND COALESCE(valid_to,'9999-12-31')>=:start LIMIT 1"
                                ),
                                {
                                    "player": row["player_id"],
                                    "team": row["team_id"],
                                    "start": row["valid_from"],
                                    "end": row.get("valid_to") or "9999-12-31",
                                },
                            ).first()
                            if overlap:
                                raise ValueError(
                                    "Membership interval overlaps existing evidence."
                                )
                        if table in OWNED:
                            row["ownership"] = "api"
                        result_fields = {}
                        if table == "matches":
                            result_fields = {
                                name: row.pop(name)
                                for name in RESULT_FIELDS
                                if name in row
                            }
                        if current is None:
                            names = ", ".join(f'"{name}"' for name in row)
                            binds = ", ".join(f":{name}" for name in row)
                            connection.execute(
                                text(
                                    f'INSERT INTO "{table}" ({names}) VALUES ({binds})'
                                ),
                                row,
                            )
                            inserted += 1
                            current = self._find(connection, table, key)
                        else:
                            # Missing or explicit unknown fields never erase known API values.
                            patch = {
                                name: value
                                for name, value in row.items()
                                if name not in key
                                and value is not None
                                and current[name] != value
                            }
                            if patch:
                                if "version" in columns:
                                    patch["version"] = current["version"] + 1
                                assignments = ", ".join(
                                    f'"{name}"=:{name}' for name in patch
                                )
                                clauses = " AND ".join(
                                    f'"{name}"=:key_{name}' for name in key
                                )
                                connection.execute(
                                    text(
                                        f'UPDATE "{table}" SET {assignments} WHERE {clauses}'
                                    ),
                                    {
                                        **patch,
                                        **{
                                            f"key_{name}": value
                                            for name, value in key.items()
                                        },
                                    },
                                )
                                updated += 1
                        if table == "matches":
                            touched_matches.add(current["match_id"])
                            deferred.append((current["match_id"], result_fields))
                for match_id, fields in deferred:
                    if fields:
                        current = self._find(
                            connection, "matches", {"match_id": match_id}
                        )
                        result = {name: current[name] for name in RESULT_FIELDS}
                        result.update(
                            {
                                name: value
                                for name, value in fields.items()
                                if value is not None
                            }
                        )
                        if result["result_type"] != "win":
                            result.update(
                                winner_team_id=None, margin_value=None, margin_unit=None
                            )
                        names = ", ".join(f'"{name}"=:{name}' for name in result)
                        connection.execute(
                            text(f"UPDATE matches SET {names} WHERE match_id=:id"),
                            {**result, "id": match_id},
                        )
                for match_id in touched_matches:
                    teams = connection.execute(
                        text("SELECT COUNT(*) FROM match_teams WHERE match_id=:id"),
                        {"id": match_id},
                    ).scalar_one()
                    if teams != 2:
                        raise ValueError(
                            "A match import must resolve exactly two participants."
                        )
                connection.execute(
                    text(
                        "UPDATE import_batches SET status='committed' WHERE batch_id=:id"
                    ),
                    {"id": batch_id},
                )
                return ImportResult("committed", batch_id, inserted, updated, skipped)
        except APIError:
            raise
        except (SQLAlchemyError, ValueError, KeyError, TypeError):
            raise APIError(
                "ingestion", "Snapshot import rejected; all changes were rolled back."
            ) from None
