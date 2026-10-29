"""CRUD for batting, bowling and fielding at innings/player grain."""

from sqlalchemy import text

from database.repositories import StaleRecordError
from models.records import validate_record
from services._crud import change, find, insert, lifecycle, positive, stamp, write

FIELDS = {
    "batting": {
        "batting_position": "INTEGER",
        "runs": "INTEGER",
        "balls_faced": "INTEGER",
        "fours": "INTEGER",
        "sixes": "INTEGER",
        "is_dismissed": "INTEGER",
        "dismissal_text": "TEXT",
    },
    "bowling": {
        "legal_balls": "INTEGER",
        "runs_conceded": "INTEGER",
        "wickets": "INTEGER",
        "maidens": "INTEGER",
    },
    "fielding": {"catches": "INTEGER", "stumpings": "INTEGER"},
}


def table_for(kind):
    """Map a supported statistic kind to its fixed persistence table."""
    if kind not in FIELDS:
        raise ValueError("Choose batting, bowling or fielding.")
    return kind + "_performances"


def validate_stats(kind, fields):
    """Validate writable fields for the selected statistic category."""
    table_for(kind)
    if not isinstance(fields, dict) or not fields:
        raise ValueError("Supply at least one statistic.")
    return validate_record(fields, FIELDS[kind])


def validate_combined(kind, row):
    """Check cross-field statistic invariants after merging proposed changes."""
    if kind == "batting":
        runs = row.get("runs")
        boundaries = 4 * (row.get("fours") or 0) + 6 * (row.get("sixes") or 0)
        if runs is not None and boundaries > runs:
            raise ValueError("Boundary runs exceed the batting total.")
        if (
            row.get("batting_position") is not None
            and not 1 <= row["batting_position"] <= 11
        ):
            raise ValueError("Batting position must be between 1 and 11.")
    if kind == "bowling":
        if row.get("wickets") is not None and row["wickets"] > 10:
            raise ValueError("Wickets cannot exceed ten in an innings.")
        if (
            row.get("maidens") is not None
            and row.get("legal_balls") is not None
            and row["maidens"] * 6 > row["legal_balls"]
        ):
            raise ValueError("Maiden overs exceed legal balls bowled.")


def relationship(c, kind, key, match_id=None, team_id=None):
    """Require the player, innings and side to form a valid statistic relationship."""
    player = find(c, "players", {"player_id": key["player_id"]})
    inning = find(c, "innings", {"innings_id": key["innings_id"]})
    if player is None or player["is_deleted"] or inning is None:
        raise ValueError("An active player and existing innings are required.")
    side = "batting_team_id" if kind == "batting" else "bowling_team_id"
    if match_id is not None and match_id != inning["match_id"]:
        raise ValueError("Innings does not belong to that match.")
    if team_id is not None and team_id != inning[side]:
        raise ValueError("Statistics belong to the wrong innings team.")
    participant = find(
        c,
        "match_players",
        {"match_id": inning["match_id"], "player_id": key["player_id"]},
    )
    if participant is None or participant["team_id"] != inning[side]:
        raise ValueError("Player is not recorded for the required match team.")
    return inning["match_id"], inning[side]


class MatchStatsService:
    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def get(self, kind, innings_id, player_id, *, include_deleted=False):
        """Read a selected record, optionally including soft-deleted rows."""
        table = table_for(kind)
        key = {
            "innings_id": positive(innings_id, "Innings ID"),
            "player_id": positive(player_id, "Player ID"),
        }
        with self.database.transaction() as c:
            row = find(c, table, key)
            player = find(c, "players", {"player_id": player_id})
            return (
                row
                if row
                and (
                    include_deleted
                    or (not row["is_deleted"] and player and not player["is_deleted"])
                )
                else None
            )

    def list(self, kind, player_id):
        """Return active records for browsing without modifying their stored state."""
        table = table_for(kind)
        positive(player_id, "Player ID")
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.execute(
                    text(
                        f"SELECT s.* FROM {table} s JOIN v_active_players p ON p.player_id=s.player_id "
                        "WHERE s.player_id=:id AND s.is_deleted=0 ORDER BY s.match_id,s.innings_id"
                    ),
                    {"id": player_id},
                ).mappings()
            ]

    def create(self, kind, innings_id, player_id, match_id, team_id, fields):
        """Validate a new record and its relationships before committing it transactionally."""
        table = table_for(kind)
        clean = validate_stats(kind, fields)
        validate_combined(kind, clean)
        if not any(v is not None for v in clean.values()):
            raise ValueError("At least one known statistic is required.")
        key = {
            "innings_id": positive(innings_id, "Innings ID"),
            "player_id": positive(player_id, "Player ID"),
        }
        positive(match_id, "Match ID")
        positive(team_id, "Team ID")
        with write(self.database) as c:
            relationship(c, kind, key, match_id, team_id)
            insert(
                c,
                table,
                {
                    **key,
                    "match_id": match_id,
                    "team_id": team_id,
                    **clean,
                    "ownership": "manual",
                    "updated_at": stamp(),
                },
            )
            return find(c, table, key)

    def update(
        self, kind, innings_id, player_id, expected_version, fields, *, override=False
    ):
        """Validate requested edits and enforce expected version and ownership rules."""
        return self._mutate(
            kind,
            innings_id,
            player_id,
            expected_version,
            "update",
            validate_stats(kind, fields),
            override,
        )

    def delete(self, kind, innings_id, player_id, expected_version, *, override=False):
        """Soft-delete the selected record with version and API-ownership checks."""
        return self._mutate(
            kind, innings_id, player_id, expected_version, "delete", {}, override
        )

    def restore(self, kind, innings_id, player_id, expected_version, *, override=False):
        """Restore a soft-deleted record after checking version and dependency rules."""
        return self._mutate(
            kind, innings_id, player_id, expected_version, "restore", {}, override
        )

    def release_override(self, kind, innings_id, player_id, expected_version):
        """Return an active operator override to provider control explicitly."""
        return self._mutate(
            kind, innings_id, player_id, expected_version, "release", {}, False
        )

    def _mutate(self, kind, innings_id, player_id, version, action, fields, override):
        """Apply one validated lifecycle change within a version-checked write transaction."""
        table = table_for(kind)
        key = {
            "innings_id": positive(innings_id, "Innings ID"),
            "player_id": positive(player_id, "Player ID"),
        }
        positive(version, "Expected version")
        with write(self.database) as c:
            current = find(c, table, key)
            if current is None or current["version"] != version:
                raise StaleRecordError(
                    "Statistics changed or are missing; reload before editing."
                )
            if action in {"update", "restore", "release"}:
                relationship(c, kind, key)
            if current["is_deleted"] and action == "update":
                raise ValueError("Restore the statistics before editing.")
            validate_combined(kind, {**current, **fields})
            policy = lifecycle(current, action, override)
            return change(c, table, key, version, {**fields, **policy})
