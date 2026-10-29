"""Explicit, additive schema migration with a no-overwrite backup."""

import argparse
import os
import sqlite3
from pathlib import Path

from config import PROJECT_ROOT, load_settings
from database.initialize import _apply_script
from utils.db_connection import DatabaseError, bootstrap_connection


def migrate_to_v2(settings) -> Path | None:
    """Back up schema 1, add ingestion metadata atomically, preserve content."""
    if settings.database_url:
        raise DatabaseError(
            "Server databases initialize at schema 2; SQLite migration does not apply."
        )
    if settings.access_mode != "local" or not settings.database_path.is_file():
        raise DatabaseError("Migration requires an existing local operator database.")
    with bootstrap_connection(settings.database_path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version == 2:
            return None
        if version != 1:
            raise DatabaseError("Unsupported migration source version.")
        mode = connection.execute(
            "SELECT mode FROM dataset_state WHERE singleton_id=1"
        ).fetchone()
        if mode is None or mode[0] != settings.data_mode:
            raise DatabaseError("Database dataset mode does not match DATA_MODE.")
        backup = Path(str(settings.database_path) + ".v1-backup")
        descriptor = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            destination = sqlite3.connect(backup)
            try:
                connection.backup(destination)
            finally:
                destination.close()
        except Exception:
            backup.unlink(missing_ok=True)
            raise
        connection.execute("BEGIN IMMEDIATE")
        try:
            if connection.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise DatabaseError(
                    "Schema changed during migration; reload the database."
                )
            _apply_script(
                connection, PROJECT_ROOT / "sql/migrations/002_ingestion_metadata.sql"
            )
            connection.execute("PRAGMA user_version=2")
            if connection.execute("PRAGMA foreign_key_check").fetchall():
                raise DatabaseError("Migration failed foreign-key validation.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return backup


def main():
    """Migrate only after explicit operator invocation, never on application open."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        backup = migrate_to_v2(load_settings())
        print(
            "Schema is already version 2."
            if backup is None
            else "Migrated to schema 2; original backup retained."
        )
    except (OSError, sqlite3.Error, DatabaseError):
        parser.exit(
            1, "Migration rejected or failed; inspect mode, schema and backup target.\n"
        )


if __name__ == "__main__":
    main()
