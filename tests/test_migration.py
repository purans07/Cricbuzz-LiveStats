"""The new additive schema migration is explicit, backed up and non-destructive."""

import sqlite3
from dataclasses import replace

import pytest

from config import PROJECT_ROOT, load_settings
from database.migrate import migrate_to_v2
from utils.db_connection import DatabaseError


@pytest.fixture
def legacy(tmp_path):
    settings = replace(load_settings(environ={}), database_path=tmp_path / "legacy.db")
    connection = sqlite3.connect(settings.database_path)
    connection.executescript((PROJECT_ROOT / "sql/schema.sql").read_text())
    connection.execute("INSERT INTO dataset_state VALUES (1,'sample',7)")
    connection.execute(
        "INSERT INTO players(player_id,full_name,updated_at) VALUES (1,'Keep this player','2026-10-21T00:00:00Z')"
    )
    connection.execute("PRAGMA user_version=1")
    connection.commit()
    connection.close()
    return settings


def test_migration_preserves_data_revision_and_original_backup(legacy):
    with sqlite3.connect(legacy.database_path) as original:
        original_dump = list(original.iterdump())
    backup = migrate_to_v2(legacy)
    assert backup.exists()
    with sqlite3.connect(backup) as saved:
        assert list(saved.iterdump()) == original_dump
        assert saved.execute("PRAGMA user_version").fetchone()[0] == 1
    with sqlite3.connect(legacy.database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert (
            connection.execute("SELECT full_name FROM players").fetchone()[0]
            == "Keep this player"
        )
        assert (
            connection.execute("SELECT revision FROM dataset_state").fetchone()[0] == 7
        )
        assert {"resource_key", "snapshot_key"} <= {
            r[1] for r in connection.execute("PRAGMA table_info(import_batches)")
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert migrate_to_v2(legacy) is None


def test_existing_backup_not_overwritten(legacy):
    backup = legacy.database_path.with_name("legacy.db.v1-backup")
    backup.write_bytes(b"Existing backup")
    before = legacy.database_path.read_bytes()
    with pytest.raises(FileExistsError):
        migrate_to_v2(legacy)
    assert backup.read_bytes() == b"Existing backup"
    assert legacy.database_path.read_bytes() == before


def test_mode_mismatch_prevents_migration(legacy):
    with pytest.raises(DatabaseError, match="mode"):
        migrate_to_v2(replace(legacy, data_mode="live"))
    assert not legacy.database_path.with_name("legacy.db.v1-backup").exists()


def test_unsupported_schema_not_touched(legacy):
    with sqlite3.connect(legacy.database_path) as connection:
        connection.execute("PRAGMA user_version=999")
    with pytest.raises(DatabaseError, match="version"):
        migrate_to_v2(legacy)
