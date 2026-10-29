"""Database persistence, bootstrap safety and transaction integrity checks."""

import json
import sqlite3
from dataclasses import replace

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from config import PROJECT_ROOT
from database.initialize import initialize_database, inspect_database
from database.repositories import (
    PlayerRepository,
    StaleRecordError,
    dataset_status,
    list_performances,
    stored_query,
)
from utils.db_connection import Database, DatabaseError


def test_schema_health_and_data(settings):
    report = inspect_database(settings)
    assert report == {
        "mode": "sample",
        "revision": 1,
        "tables": 21,
        "views": 6,
        "indexes": 19,
        "players": 12,
        "matches": 72,
        "innings": 192,
        "career_stats_snapshots": 72,
        "foreign_keys": 1,
        "integrity": "ok",
    }


def test_reinitialize_preserves_every_byte(settings):
    before = settings.database_path.read_bytes()
    with pytest.raises(FileExistsError):
        initialize_database(settings, seed_sample=True)
    assert settings.database_path.read_bytes() == before


def test_failure_does_not_publish_or_leave_partial_file(settings, tmp_path):
    payload = json.loads((PROJECT_ROOT / "data/sample/seed.json").read_text())
    payload["tables"][-1]["rows"][0]["player_id"] = 999999
    seed = tmp_path / "bad.json"
    seed.write_text(json.dumps(payload))
    target = tmp_path / "failed.db"
    with pytest.raises(sqlite3.IntegrityError):
        initialize_database(
            replace(settings, database_path=target), seed_sample=True, seed_path=seed
        )
    assert not target.exists()
    assert list(tmp_path.glob(".initializing-*")) == []


def test_live_database_is_empty_and_rejects_synthetic_seeds(settings, tmp_path):
    live = replace(settings, data_mode="live", database_path=tmp_path / "live.db")
    with pytest.raises(ValueError):
        initialize_database(live, seed_sample=True)
    assert not live.database_path.exists()
    initialize_database(live)
    assert inspect_database(live)["players"] == 0
    assert inspect_database(live)["revision"] == 0


def test_sample_live_mismatch_rejected(settings):
    wrong = Database(replace(settings, data_mode="live"))
    try:
        with pytest.raises(DatabaseError, match="mode"):
            with wrong.transaction():
                pass
    finally:
        wrong.close()


def test_missing_database_not_created(settings, tmp_path):
    path = tmp_path / "absent.db"
    db = Database(replace(settings, database_path=path))
    try:
        with pytest.raises(DatabaseError):
            with db.transaction(write=True):
                pass
        assert not path.exists()
    finally:
        db.close()


def test_foreign_keys_on_all_connections(database):
    for write in (False, True, False, True):
        with database.transaction(write=write) as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE batting_performances SET team_id=2 WHERE innings_id=11",
        "UPDATE bowling_performances SET team_id=1 WHERE innings_id=11",
        "UPDATE fielding_performances SET team_id=1 WHERE innings_id=11",
        "UPDATE batting_performances SET runs=-1 WHERE innings_id=11",
        "DELETE FROM players WHERE player_id=1",
        "INSERT INTO match_teams VALUES (1, 1, 3)",
        "UPDATE players SET external_id='fixture-player-2' WHERE player_id=1",
    ],
)
def test_invalid_changes_rollback(database, statement):
    with pytest.raises(IntegrityError):
        with database.transaction(write=True) as connection:
            connection.exec_driver_sql(statement)
    with database.transaction() as connection:
        assert dataset_status(connection)["revision"] == 1
        assert PlayerRepository.get(connection, 1)["full_name"] == "Sample Player 01"


def test_atomic_rollback_restores_profile_and_revision(database):
    with pytest.raises(IntegrityError):
        with database.transaction(write=True) as connection:
            connection.exec_driver_sql(
                "UPDATE players SET full_name='Should roll back' WHERE player_id=1"
            )
            connection.exec_driver_sql(
                "UPDATE batting_performances SET runs=-1 WHERE innings_id=11"
            )
    with database.transaction() as connection:
        assert PlayerRepository.get(connection, 1)["full_name"] == "Sample Player 01"
        assert dataset_status(connection)["revision"] == 1


def test_successful_multiwrite_persists_and_increments_once(database, settings):
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql(
            "UPDATE players SET full_name='Changed A' WHERE player_id=1"
        )
        connection.exec_driver_sql(
            "UPDATE players SET full_name='Changed B' WHERE player_id=2"
        )
    reopened = Database(settings)
    try:
        with reopened.transaction() as connection:
            assert PlayerRepository.get(connection, 1)["full_name"] == "Changed A"
            assert dataset_status(connection)["revision"] == 2
    finally:
        reopened.close()


def test_noop_transaction_does_not_increment(database):
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql("SELECT 1")
    with database.transaction() as connection:
        assert dataset_status(connection)["revision"] == 1


def test_reader_cannot_modify_main_database(database):
    with pytest.raises(DBAPIError):
        with database.transaction() as connection:
            connection.exec_driver_sql("UPDATE players SET full_name='Forbidden'")


def test_public_mode_cannot_write_or_initialize(settings, tmp_path):
    public = replace(settings, access_mode="public_readonly")
    db = Database(public)
    try:
        with pytest.raises(DatabaseError):
            with db.transaction(write=True):
                pass
        with db.transaction() as connection:
            assert len(PlayerRepository.list_active(connection)) == 12
        with pytest.raises(DatabaseError):
            initialize_database(replace(public, database_path=tmp_path / "new.db"))
    finally:
        db.close()


def test_tombstoned_players_and_performances_excluded(database):
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
        connection.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE innings_id=11 AND player_id=2"
        )
    with database.transaction() as connection:
        assert PlayerRepository.get(connection, 1) is None
        for kind in ("batting", "bowling", "fielding"):
            assert list_performances(connection, kind, 1) == []
        assert all(
            r["innings_id"] != 11 for r in list_performances(connection, "batting", 2)
        )
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM v_latest_career WHERE player_id=1"
            ).scalar_one()
            == 0
        )


def test_super_over_excluded_from_ordinary_views(database):
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql(
            "UPDATE innings SET is_super_over=1 WHERE innings_id=11"
        )
    with database.transaction() as connection:
        assert all(
            r["innings_id"] != 11 for r in list_performances(connection, "batting", 1)
        )


def test_latest_career_excludes_uncommitted_and_does_not_sum(database):
    with database.transaction() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT COUNT(*) FROM v_latest_career"
            ).scalar_one()
            == 36
        )
        assert connection.exec_driver_sql(
            "SELECT DISTINCT batch_id FROM v_latest_career"
        ).scalars().all() == [2]
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql(
            "UPDATE import_batches SET status='failed' WHERE batch_id=2"
        )
    with database.transaction() as connection:
        assert connection.exec_driver_sql(
            "SELECT DISTINCT batch_id FROM v_latest_career"
        ).scalars().all() == [1]


def test_version_checked_profile_patch_and_parameter_binding(database):
    name = "O'Brien; DROP TABLE players; --"
    with database.transaction(write=True) as connection:
        PlayerRepository.update_profile(
            connection,
            1,
            1,
            {
                "full_name": name,
                "updated_at": "2026-10-21T12:00:00Z",
            },
        )
    with pytest.raises(StaleRecordError):
        with database.transaction(write=True) as connection:
            PlayerRepository.update_profile(
                connection,
                1,
                1,
                {
                    "full_name": "Stale",
                    "updated_at": "2026-10-21T12:00:00Z",
                },
            )
    with database.transaction() as connection:
        row = PlayerRepository.get(connection, 1)
        assert row["full_name"] == name
        assert row["version"] == 2
        assert dataset_status(connection)["revision"] == 2


def test_identifier_allowlists(database):
    with pytest.raises(ValueError):
        stored_query("../../.env")
    with database.transaction() as connection:
        with pytest.raises(ValueError):
            list_performances(connection, "players; DELETE FROM players", 1)


def test_index_used_for_player_match_lookup(database):
    with database.transaction() as connection:
        plan = connection.exec_driver_sql(
            "EXPLAIN QUERY PLAN SELECT * FROM batting_performances WHERE player_id=1 AND match_id=1"
        ).fetchall()
        assert any("idx_batting_player_match" in row[3] for row in plan)
        assert connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []


def test_wrong_schema_version_is_rejected(settings):
    connection = sqlite3.connect(settings.database_path)
    connection.execute("PRAGMA user_version=999")
    connection.close()
    db = Database(settings)
    try:
        with pytest.raises(DatabaseError, match="version"), db.transaction():
            pass
    finally:
        db.close()


def test_unknown_batting_value_remains_null(database):
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql(
            "UPDATE batting_performances SET runs=NULL WHERE innings_id=11 AND player_id=1"
        )
    with database.transaction() as connection:
        row = list_performances(connection, "batting", 1)[0]
        assert row["runs"] is None
        assert row["balls_faced"] > 0


def test_latest_snapshots_do_not_merge_sources(database):
    with database.transaction(write=True) as connection:
        connection.exec_driver_sql(
            "INSERT INTO sources VALUES (3, 'Other synthetic source', 'sample')"
        )
        connection.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) "
            "VALUES (3,3,'fixture','2026-10-02T00:00:00Z','partial','committed')"
        )
        connection.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,runs) "
            "VALUES (1,1,3,999)"
        )
    with database.transaction() as connection:
        rows = connection.exec_driver_sql(
            "SELECT source_id,runs FROM v_latest_career WHERE player_id=1 AND format_id=1 ORDER BY source_id"
        ).fetchall()
        assert rows == [(1, 1660), (3, 999)]


def test_unlabeled_seed_is_rejected_without_publication(settings, tmp_path):
    seed = tmp_path / "unlabeled.json"
    seed.write_text('{"metadata": {}, "tables": []}')
    target = tmp_path / "unlabeled.db"
    with pytest.raises(ValueError, match="synthetic"):
        initialize_database(
            replace(settings, database_path=target), seed_sample=True, seed_path=seed
        )
    assert not target.exists()
