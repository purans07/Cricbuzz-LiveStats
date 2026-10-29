"""Validated player CRUD with reversible deletion and explicit API overrides."""

from sqlalchemy import text

from database.repositories import StaleRecordError
from models.records import validate_record
from services._crud import change, find, insert, lifecycle, positive, stamp, write

PROFILE_FIELDS = {
    "full_name": "TEXT",
    "role_id": "INTEGER",
    "batting_style": "TEXT",
    "bowling_style": "TEXT",
}


def validate_profile(fields):
    """Validate editable player fields while preserving required identity rules."""
    if not isinstance(fields, dict) or not fields:
        raise ValueError("Supply at least one player field.")
    clean = validate_record(fields, PROFILE_FIELDS)
    if "full_name" in clean and clean["full_name"] is None:
        raise ValueError("Player name is required.")
    if clean.get("role_id") is not None:
        positive(clean["role_id"], "Role ID")
    return clean


class PlayerService:
    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def get(self, player_id, *, include_deleted=False):
        """Read a selected record, optionally including soft-deleted rows."""
        positive(player_id, "Player ID")
        with self.database.transaction() as c:
            row = find(c, "players", {"player_id": player_id})
            return row if row and (include_deleted or not row["is_deleted"]) else None

    def list(self):
        """Return active records for browsing without modifying their stored state."""
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.execute(
                    text("SELECT * FROM v_active_players ORDER BY player_id")
                ).mappings()
            ]

    def create(self, fields):
        """Validate a new record and its relationships before committing it transactionally."""
        clean = validate_profile(fields)
        if not clean.get("full_name"):
            raise ValueError("Player name is required.")
        with write(self.database) as c:
            result = insert(
                c, "players", {**clean, "ownership": "manual", "updated_at": stamp()}
            )
            return find(c, "players", {"player_id": result.lastrowid})

    def update(self, player_id, expected_version, fields, *, override=False):
        """Validate requested edits and enforce expected version and ownership rules."""
        return self._mutate(
            player_id, expected_version, "update", validate_profile(fields), override
        )

    def delete(self, player_id, expected_version, *, override=False):
        """Soft-delete the selected record with version and API-ownership checks."""
        return self._mutate(player_id, expected_version, "delete", {}, override)

    def restore(self, player_id, expected_version, *, override=False):
        """Restore a soft-deleted record after checking version and dependency rules."""
        return self._mutate(player_id, expected_version, "restore", {}, override)

    def release_override(self, player_id, expected_version):
        """Allow a later successful API refresh to replace local corrections."""
        return self._mutate(player_id, expected_version, "release", {}, False)

    def _mutate(self, player_id, version, action, fields, override):
        """Apply one validated lifecycle change within a version-checked write transaction."""
        positive(player_id, "Player ID")
        positive(version, "Expected version")
        with write(self.database) as c:
            key = {"player_id": player_id}
            current = find(c, "players", key)
            if current is None or current["version"] != version:
                raise StaleRecordError(
                    "Player changed or is missing; reload before editing."
                )
            if current["is_deleted"] and action == "update":
                raise ValueError("Restore the player before editing.")
            policy = lifecycle(current, action, override)
            return change(c, "players", key, version, {**fields, **policy})
