"""Persistence primitives; callers own the transaction and business rules."""

from sqlalchemy import text

from config import PROJECT_ROOT
from models.records import validate_record

PERFORMANCE_VIEWS = {
    "batting": "v_active_batting",
    "bowling": "v_active_bowling",
    "fielding": "v_active_fielding",
}
PLAYER_COLUMNS = {
    "full_name": "TEXT",
    "role_id": "INTEGER",
    "batting_style": "TEXT",
    "bowling_style": "TEXT",
    "ownership": "TEXT",
    "is_deleted": "INTEGER",
    "updated_at": "TEXT",
}


class StaleRecordError(ValueError):
    """The selected record changed or no longer exists."""


def stored_query(name: str) -> str:
    """Load an allowlisted operational query, excluding arbitrary paths."""
    if name not in {"dataset_status", "player_by_id"}:
        raise ValueError("Unknown operational query.")
    return (PROJECT_ROOT / "sql" / "queries" / f"{name}.sql").read_text()


class PlayerRepository:
    """Read active profiles and apply version-checked persistence patches."""

    @staticmethod
    def get(connection, player_id: int):
        """Return one active profile, or None; values are bound parameters."""
        return (
            connection.execute(
                text(stored_query("player_by_id")), {"player_id": player_id}
            )
            .mappings()
            .first()
        )

    @staticmethod
    def list_active(connection):
        """Read active players in stable identity order."""
        return (
            connection.execute(
                text("SELECT * FROM v_active_players ORDER BY player_id")
            )
            .mappings()
            .all()
        )

    @staticmethod
    def update_profile(connection, player_id: int, expected_version: int, fields: dict):
        """Apply an allowlisted patch; services must enforce ownership policy."""
        if not fields or "updated_at" not in fields:
            raise ValueError("A profile patch requires fields and updated_at.")
        clean = validate_record(fields, PLAYER_COLUMNS)
        assignments = ", ".join(f'"{key}" = :{key}' for key in clean)
        result = connection.execute(
            text(
                f"UPDATE players SET {assignments}, version = version + 1 "
                "WHERE player_id = :record_id AND version = :expected_version"
            ),
            {**clean, "record_id": player_id, "expected_version": expected_version},
        )
        if result.rowcount != 1:
            raise StaleRecordError(
                "Player changed or is missing; reload before editing."
            )


def list_performances(connection, kind: str, player_id: int):
    """Read active ordinary-innings performances from a fixed view allowlist."""
    try:
        view = PERFORMANCE_VIEWS[kind]
    except KeyError:
        raise ValueError(
            "Performance kind must be batting, bowling or fielding."
        ) from None
    return (
        connection.execute(
            text(
                f"SELECT * FROM {view} WHERE player_id = :player_id "
                "ORDER BY match_id, innings_id"
            ),
            {"player_id": player_id},
        )
        .mappings()
        .all()
    )


def dataset_status(connection):
    """Read mode/revision without solving analytical assignment questions."""
    return connection.execute(text(stored_query("dataset_status"))).mappings().one()
