"""Player service lifecycle, versioning, ownership, and readonly boundaries."""

from dataclasses import replace

import pytest

from database.repositories import StaleRecordError
from services._crud import OwnershipError
from services.players import PlayerService
from utils.db_connection import Database, DatabaseError


def revision(db):
    with db.transaction() as c:
        return c.exec_driver_sql("SELECT revision FROM dataset_state").scalar_one()


def test_create_patch_delete_restore_and_noop(database):
    service = PlayerService(database)
    base = revision(database)
    row = service.create({"full_name": "Local Player '); DROP TABLE players; --"})
    assert row["ownership"] == "manual" and row["version"] == 1
    assert service.get(row["player_id"])["full_name"] == row["full_name"]
    same = service.update(row["player_id"], 1, {"full_name": row["full_name"]})
    assert same["version"] == 1 and revision(database) == base + 1
    row = service.update(
        row["player_id"], 1, {"batting_style": "Left hand", "bowling_style": None}
    )
    assert row["version"] == 2
    row = service.delete(row["player_id"], 2)
    assert service.get(row["player_id"]) is None
    assert service.get(row["player_id"], include_deleted=True)["is_deleted"] == 1
    assert all(p["player_id"] != row["player_id"] for p in service.list())
    row = service.restore(row["player_id"], row["version"])
    assert service.get(row["player_id"])["is_deleted"] == 0
    assert revision(database) == base + 4


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"full_name": " "},
        {"full_name": None},
        {"ownership": "api"},
        {"source_id": 1},
        {"version": 9},
        {"role_id": 999999},
        {"role_id": True},
    ],
)
def test_invalid_profile_changes_rollback(database, fields):
    service = PlayerService(database)
    before = revision(database)
    with pytest.raises(ValueError):
        service.update(1, 1, fields)
    assert revision(database) == before
    assert service.get(1)["version"] == 1


def test_stale_edits_and_deleted_edit_do_not_change_revision(database):
    service = PlayerService(database)
    row = service.update(1, 1, {"full_name": "First edit"})
    before = revision(database)
    with pytest.raises(StaleRecordError):
        service.update(1, 1, {"full_name": "Old screen edit"})
    assert revision(database) == before
    row = service.delete(1, row["version"])
    before = revision(database)
    with pytest.raises(ValueError, match="Restore"):
        service.update(1, row["version"], {"full_name": "Hidden edit"})
    assert revision(database) == before


def test_public_readonly_denies_every_mutation(settings):
    db = Database(replace(settings, access_mode="public_readonly"))
    try:
        service = PlayerService(db)
        assert service.get(1)
        for operation in (
            lambda: service.create({"full_name": "Forbidden"}),
            lambda: service.update(1, 1, {"full_name": "Forbidden"}),
            lambda: service.delete(1, 1),
            lambda: service.restore(1, 1),
        ):
            with pytest.raises(DatabaseError):
                operation()
    finally:
        db.close()


def test_manual_profile_cannot_be_released_to_api(database):
    with pytest.raises(OwnershipError):
        PlayerService(database).release_override(1, 1)
