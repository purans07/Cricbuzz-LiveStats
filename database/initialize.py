"""Safely build a new database and atomically publish it without replacement."""

import argparse
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from config import PROJECT_ROOT, Settings, load_settings
from models.records import validate_record
from utils.db_connection import Database, DatabaseError, bootstrap_connection

SCHEMA_VERSION = 2


def _statements(script: str):
    """Split reviewed local SQL with SQLite's parser, not a semicolon split."""
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ""
    if re.sub(r"--[^\n]*", "", pending).strip():
        raise ValueError("SQL script has an incomplete statement.")


def _apply_script(connection, path: Path):
    """Execute DDL within the caller's single bootstrap transaction."""
    for statement in _statements(path.read_text()):
        body = re.sub(r"--[^\n]*", "", statement).strip().rstrip(";").strip()
        if body.upper() in {"BEGIN", "COMMIT", "PRAGMA FOREIGN_KEYS = ON"}:
            continue
        connection.execute(statement)


def _load_seed(connection, path: Path):
    """Validate and insert a reviewed synthetic dataset in dependency order."""
    payload = json.loads(path.read_text())
    if payload.get("metadata", {}).get("synthetic") is not True:
        raise ValueError("Seed input must be explicitly marked synthetic.")
    allowed = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    } - {"dataset_state"}
    for group in payload["tables"]:
        table = group["table"]
        if table not in allowed:
            raise ValueError("Seed contains an unknown or reserved table.")
        column_types = {
            row[1]: row[2]
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        }
        for row in group["rows"]:
            record = validate_record(row, column_types)
            if not record:
                raise ValueError("Seed rows must contain fields.")
            columns = ", ".join(f'"{key}"' for key in record)
            placeholders = ", ".join("?" for _ in record)
            connection.execute(
                f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
                tuple(record.values()),
            )
    # Match rows must exist before participants, then apply cyclic result FKs.
    for result in payload.get("match_results", []):
        clean = validate_record(
            result,
            {
                "match_id": "INTEGER",
                "winner_team_id": "INTEGER",
                "toss_winner_id": "INTEGER",
                "toss_decision": "TEXT",
                "result_type": "TEXT",
                "margin_value": "INTEGER",
                "margin_unit": "TEXT",
            },
        )
        match_id = clean.pop("match_id")
        assignments = ", ".join(f'"{key}" = ?' for key in clean)
        cursor = connection.execute(
            f"UPDATE matches SET {assignments} WHERE match_id = ?",
            (*clean.values(), match_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Seed result refers to a missing match.")


def initialize_database(
    settings: Settings,
    *,
    seed_sample: bool = False,
    seed_path: Path | None = None,
) -> Path:
    """Create a fresh database atomically; never reset or seed an existing file."""
    if settings.database_url:
        raise DatabaseError(
            "Use python -m database.server for explicit server initialization."
        )
    if settings.access_mode != "local":
        raise DatabaseError("Initialization requires local operator mode.")
    if seed_sample and settings.data_mode != "sample":
        raise ValueError("Synthetic seed data is permitted only in sample mode.")
    target = settings.database_path
    if target.exists():
        raise FileExistsError(
            "Database already exists; initialization never overwrites it."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(
        prefix=".initializing-", suffix=".db", dir=target.parent
    )
    os.close(handle)
    temporary = Path(name)
    try:
        with bootstrap_connection(temporary) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                _apply_script(connection, PROJECT_ROOT / "sql" / "schema.sql")
                _apply_script(
                    connection,
                    PROJECT_ROOT / "sql/migrations/002_ingestion_metadata.sql",
                )
                _apply_script(connection, PROJECT_ROOT / "sql" / "views.sql")
                connection.execute(
                    "INSERT INTO dataset_state VALUES (1, ?, ?)",
                    (settings.data_mode, 1 if seed_sample else 0),
                )
                if seed_sample:
                    _load_seed(
                        connection, seed_path or PROJECT_ROOT / "data/sample/seed.json"
                    )
                if connection.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("Seed violates foreign-key integrity.")
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity validation failed.")
        # Hard-link publication fails if another process created target meanwhile.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def inspect_database(settings: Settings) -> dict:
    """Return a small operational health report using a read-only connection."""
    database = Database(settings)
    try:
        if settings.database_url:
            from sqlalchemy import inspect

            with database.transaction() as connection:
                inspector = inspect(connection)
                tables = inspector.get_table_names()
                result = dict(
                    connection.exec_driver_sql(
                        "SELECT mode,revision FROM dataset_state WHERE singleton_id=1"
                    )
                    .mappings()
                    .one()
                )
                result.update(
                    schema_version=2,
                    tables=len(tables),
                    views=len(inspector.get_view_names()),
                    indexes=sum(len(inspector.get_indexes(t)) for t in tables),
                    backend=connection.dialect.name,
                )
                for table in (
                    "players",
                    "matches",
                    "innings",
                    "career_stats_snapshots",
                ):
                    result[table] = connection.exec_driver_sql(
                        f"SELECT COUNT(*) FROM {table}"
                    ).scalar_one()
                result["integrity"] = (
                    "schema and constraints configured; physical check not performed"
                )
                return result
        with database.transaction() as connection:
            report = dict(
                connection.exec_driver_sql(
                    "SELECT mode, revision FROM dataset_state WHERE singleton_id=1"
                )
                .mappings()
                .one()
            )
            for kind in ("table", "view", "index"):
                report[
                    {"table": "tables", "view": "views", "index": "indexes"}[kind]
                ] = connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type = ? "
                    "AND sql IS NOT NULL",
                    (kind,),
                ).scalar_one()
            for table in ("players", "matches", "innings", "career_stats_snapshots"):
                report[table] = connection.exec_driver_sql(
                    f"SELECT COUNT(*) FROM {table}"
                ).scalar_one()
            report["foreign_keys"] = connection.exec_driver_sql(
                "PRAGMA foreign_keys"
            ).scalar_one()
            report["integrity"] = connection.exec_driver_sql(
                "PRAGMA integrity_check"
            ).scalar_one()
            return report
    finally:
        database.close()


def main():
    """Expose safe init/check commands, with no destructive reset option."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Inspect without changing data"
    )
    parser.add_argument("--mode", choices=("sample", "live"))
    parser.add_argument("--database", type=Path, help="Explicit local database path")
    parser.add_argument("--seed-sample", action="store_true")
    args = parser.parse_args()
    try:
        settings = load_settings()
        if args.mode:
            if args.mode != settings.data_mode and args.database is None:
                raise ValueError("Changing mode requires an explicit --database path.")
            settings = replace(settings, data_mode=args.mode)
        if args.database:
            settings = replace(
                settings, database_path=args.database.expanduser().resolve()
            )
        if args.check:
            if args.seed_sample:
                raise ValueError("--check cannot be combined with --seed-sample.")
            print(json.dumps(inspect_database(settings), indent=2))
        else:
            target = initialize_database(settings, seed_sample=args.seed_sample)
            print(f"Created {settings.data_mode} database: {target}")
            print(json.dumps(inspect_database(settings), indent=2))
    except FileExistsError:
        parser.exit(
            1,
            "Database already exists; use --check to inspect it. "
            "No existing file was replaced.\n",
        )
    except (ValueError, DatabaseError) as error:
        parser.exit(1, f"Database operation rejected: {error}\n")
    except (OSError, sqlite3.Error, SQLAlchemyError):
        # Detailed driver errors may contain data; expose only a safe summary.
        parser.exit(
            1,
            "Database operation failed. Check mode, configuration, "
            "target existence and seed validity; no existing database was replaced.\n",
        )


if __name__ == "__main__":
    main()
