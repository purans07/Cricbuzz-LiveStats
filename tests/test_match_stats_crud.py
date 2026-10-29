"""Innings-grain CRUD, relationship validation, and API-refresh preservation."""

import json
from pathlib import Path

import pytest

from api.adapter import decode_snapshot
from database.repositories import StaleRecordError
from services._crud import OwnershipError
from services.ingestion import IngestionService
from services.match_stats import MatchStatsService
from services.players import PlayerService


def revision(db):
    with db.transaction() as c:
        return c.exec_driver_sql("SELECT revision FROM dataset_state").scalar_one()


@pytest.fixture
def participants(database):
    players = PlayerService(database)
    a = players.create({"full_name": "Local batting player"})["player_id"]
    b = players.create({"full_name": "Local bowling player"})["player_id"]
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO match_players(match_id,player_id,team_id,participation) VALUES(1,?,1,'observed'),(1,?,2,'observed')",
            (a, b),
        )
    return a, b


@pytest.mark.parametrize(
    "kind,fields,patch,side",
    [
        ("batting", {"runs": 5, "balls_faced": 3, "is_dismissed": 0}, {"runs": 6}, 1),
        (
            "bowling",
            {"legal_balls": 12, "runs_conceded": 5, "wickets": 1},
            {"wickets": 2},
            2,
        ),
        ("fielding", {"catches": 1, "stumpings": 0}, {"catches": 2}, 2),
    ],
)
def test_all_stat_lifecycles(database, participants, kind, fields, patch, side):
    s = MatchStatsService(database)
    pid = participants[side - 1]
    base = revision(database)
    row = s.create(kind, 11, pid, 1, side, fields)
    assert row["ownership"] == "manual" and row["version"] == 1
    assert s.list(kind, pid)[0]["innings_id"] == 11
    row = s.update(kind, 11, pid, 1, patch)
    assert row["version"] == 2
    with pytest.raises(StaleRecordError):
        s.delete(kind, 11, pid, 1)
    row = s.delete(kind, 11, pid, 2)
    assert s.get(kind, 11, pid) is None and s.list(kind, pid) == []
    assert s.get(kind, 11, pid, include_deleted=True)["is_deleted"] == 1
    row = s.restore(kind, 11, pid, row["version"])
    assert row["is_deleted"] == 0
    assert revision(database) == base + 4


@pytest.mark.parametrize(
    "case",
    [
        "wrong_match",
        "wrong_team",
        "wrong_player_side",
        "duplicate",
        "invalid_count",
        "boundaries",
        "maiden",
        "protected",
        "move",
        "bool",
    ],
)
def test_bad_stats_and_relationships_are_atomic(database, participants, case):
    s = MatchStatsService(database)
    before = revision(database)
    pid = participants[0]
    with pytest.raises(ValueError):
        if case == "wrong_match":
            s.create("batting", 11, pid, 2, 1, {"runs": 1})
        elif case == "wrong_team":
            s.create("batting", 11, pid, 1, 2, {"runs": 1})
        elif case == "wrong_player_side":
            s.create("batting", 11, participants[1], 1, 1, {"runs": 1})
        elif case == "duplicate":
            s.create("batting", 11, 1, 1, 1, {"runs": 1})
        elif case == "invalid_count":
            s.update("bowling", 11, 7, 1, {"wickets": 11})
        elif case == "boundaries":
            s.update("batting", 11, 1, 1, {"runs": 1})
        elif case == "maiden":
            s.update("bowling", 11, 7, 1, {"maidens": 100})
        elif case == "protected":
            s.update("batting", 11, 1, 1, {"ownership": "api"})
        elif case == "move":
            s.update("batting", 11, 1, 1, {"team_id": 2})
        else:
            s.update("batting", 11, 1, 1, {"runs": True})
    assert revision(database) == before


def test_player_delete_hides_joined_stats_and_restore_recovers(database):
    players = PlayerService(database)
    stats = MatchStatsService(database)
    assert stats.list("batting", 1)
    deleted = players.delete(1, 1)
    assert stats.list("batting", 1) == []
    assert stats.get("batting", 11, 1) is None
    with pytest.raises(ValueError):
        stats.update("batting", 11, 1, 1, {"runs": 100})
    with database.transaction() as c:
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM v_active_batting WHERE player_id=1"
            ).scalar_one()
            == 0
        )
    players.restore(1, deleted["version"])
    assert stats.get("batting", 11, 1)


def test_api_overrides_tombstones_restore_and_release_survive_refresh(database):
    payload = json.loads(
        (Path(__file__).parent / "fixtures/normalized_match.json").read_text()
    )
    ingest = IngestionService(database)
    ingest.ingest(decode_snapshot(payload))
    with database.transaction() as c:
        p = c.exec_driver_sql(
            "SELECT player_id FROM players WHERE external_id='player-alpha'"
        ).scalar_one()
        inning = c.exec_driver_sql(
            "SELECT innings_id FROM batting_performances WHERE player_id=?", (p,)
        ).scalar_one()
    players, stats = PlayerService(database), MatchStatsService(database)
    with pytest.raises(OwnershipError):
        players.update(p, 1, {"full_name": "Local correction"})
    with pytest.raises(OwnershipError):
        stats.update("batting", inning, p, 1, {"runs": 99})
    player = players.update(p, 1, {"full_name": "Local correction"}, override=True)
    performance = stats.update("batting", inning, p, 1, {"runs": 99}, override=True)
    performance = stats.delete("batting", inning, p, performance["version"])
    payload["metadata"]["fetched_at"] = "2026-10-22T10:00:00Z"
    payload["metadata"]["upstream_updated_at"] = "2026-10-22T09:59:00Z"
    ingest.ingest(decode_snapshot(payload))
    assert players.get(p)["full_name"] == "Local correction"
    assert stats.get("batting", inning, p) is None
    with pytest.raises(OwnershipError):
        stats.release_override("batting", inning, p, performance["version"])
    performance = stats.restore("batting", inning, p, performance["version"])
    stats.release_override("batting", inning, p, performance["version"])
    players.release_override(p, player["version"])
    payload["metadata"]["fetched_at"] = "2026-10-23T10:00:00Z"
    payload["metadata"]["upstream_updated_at"] = "2026-10-23T09:59:00Z"
    ingest.ingest(decode_snapshot(payload))
    assert players.get(p)["full_name"] == "Synthetic Alpha Player"
    assert stats.get("batting", inning, p)["runs"] == 60
    with database.transaction() as c:
        assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []


def test_api_player_tombstone_survives_import(database):
    payload = json.loads(
        (Path(__file__).parent / "fixtures/normalized_match.json").read_text()
    )
    ingest = IngestionService(database)
    ingest.ingest(decode_snapshot(payload))
    with database.transaction() as c:
        pid = c.exec_driver_sql(
            "SELECT player_id FROM players WHERE external_id='player-alpha'"
        ).scalar_one()
    players = PlayerService(database)
    deleted = players.delete(pid, 1, override=True)
    payload["metadata"]["fetched_at"] = "2026-10-22T10:00:00Z"
    payload["metadata"]["upstream_updated_at"] = "2026-10-22T09:59:00Z"
    ingest.ingest(decode_snapshot(payload))
    assert players.get(pid) is None
    assert players.get(pid, include_deleted=True)["version"] == deleted["version"]
    restored = players.restore(pid, deleted["version"])
    assert restored["ownership"] == "override"


def test_public_readonly_statistics_deny_writes(settings):
    from dataclasses import replace

    from utils.db_connection import Database, DatabaseError

    db = Database(replace(settings, access_mode="public_readonly"))
    try:
        s = MatchStatsService(db)
        assert s.get("batting", 11, 1)
        for action in (
            lambda: s.update("batting", 11, 1, 1, {"runs": 100}),
            lambda: s.delete("batting", 11, 1, 1),
            lambda: s.restore("batting", 11, 1, 1),
            lambda: s.create("fielding", 11, 7, 1, 2, {"catches": 1}),
        ):
            with pytest.raises(DatabaseError):
                action()
    finally:
        db.close()


def test_null_patch_and_noop_do_not_invent_zero_or_advance_version(database):
    s = MatchStatsService(database)
    current = s.get("bowling", 11, 7)
    base = revision(database)
    assert (
        s.update("bowling", 11, 7, current["version"], {"wickets": current["wickets"]})[
            "version"
        ]
        == current["version"]
    )
    assert revision(database) == base
    row = s.update("bowling", 11, 7, current["version"], {"wickets": None})
    assert row["wickets"] is None and row["version"] == current["version"] + 1
    assert revision(database) == base + 1
