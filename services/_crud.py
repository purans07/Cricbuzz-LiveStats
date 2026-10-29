"""Shared version checks and bound persistence for the Phase 10 services."""

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database.repositories import StaleRecordError
from utils.db_connection import generated_id


class OwnershipError(ValueError):
    """Editing provider-owned content requires an explicit local override."""


def positive(value, label):
    """Require a positive integer identifier and reject booleans and non-integers."""
    if type(value) is not int or value <= 0:
        raise ValueError(f"{label} must be a positive integer.")
    return value


def stamp():
    """Return a canonical UTC timestamp for persisted metadata."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def write(database):
    """Provide a transaction and translate constraint failures into a safe validation error."""
    try:
        with database.transaction(write=True) as connection:
            yield connection
    except IntegrityError:
        raise ValueError(
            "Record conflicts with an existing record or a database relationship."
        ) from None


def find(connection, table, key):
    # All table/key identifiers come from fixed service definitions, never user input.
    """Read one matching row using trusted identifiers and bound values."""
    condition = " AND ".join(f'"{k}"=:{k}' for k in key)
    row = (
        connection.execute(text(f'SELECT * FROM "{table}" WHERE {condition}'), key)
        .mappings()
        .first()
    )
    return dict(row) if row else None


def insert(connection, table, row):
    """Insert validated fields with bound values into a service-selected table."""
    names = ",".join(f'"{name}"' for name in row)
    values = ",".join(f":{name}" for name in row)
    result = connection.execute(
        text(f'INSERT INTO "{table}" ({names}) VALUES ({values})'), row
    )
    return SimpleNamespace(lastrowid=generated_id(connection, result, table))


def change(connection, table, key, version, fields):
    """Update only changed fields after checking the expected record version."""
    positive(version, "Expected version")
    current = find(connection, table, key)
    if current is None or current["version"] != version:
        raise StaleRecordError("Record changed or is missing; reload before editing.")
    clean = {k: v for k, v in fields.items() if current[k] != v}
    if not clean:
        return current
    clean["updated_at"] = stamp()
    assignments = ",".join(f'"{k}"=:new_{k}' for k in clean)
    conditions = " AND ".join(f'"{k}"=:{k}' for k in key)
    result = connection.execute(
        text(
            f'UPDATE "{table}" SET {assignments},version=version+1 '
            f"WHERE {conditions} AND version=:expected"
        ),
        {**key, "expected": version, **{f"new_{k}": v for k, v in clean.items()}},
    )
    if result.rowcount != 1:
        raise StaleRecordError("Record changed; reload before editing.")
    return find(connection, table, key)


def lifecycle(current, action, override):
    """Enforce API ownership and compute reversible delete, restore or release fields."""
    if type(override) is not bool:
        raise ValueError("Override must be explicit true or false.")
    if action == "release":
        if current["ownership"] != "override" or current["is_deleted"]:
            raise OwnershipError(
                "Restore a deleted override before releasing it to API control."
            )
        return {"ownership": "api"}
    if current["ownership"] == "api" and not override:
        raise OwnershipError("Set override=True to change an API-owned record.")
    fields = {"ownership": "override"} if current["ownership"] == "api" else {}
    if action == "delete":
        fields["is_deleted"] = 1
    elif action == "restore":
        fields["is_deleted"] = 0
    return fields
