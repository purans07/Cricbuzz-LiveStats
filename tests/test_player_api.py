"""Observed profile/career mapping, atomic refresh, and rejection boundaries."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.client import APIError, APIResponse
from api.players import CricbuzzV2PlayerNormalizer
from config import load_settings
from database.initialize import initialize_database
from services.ingestion import IngestionService
from services.player_stats import PlayerStatsService
from utils.db_connection import Database

FIXTURE = Path(__file__).parent / "fixtures/cricbuzz_v2_player_8583.json"


def responses():
    return [APIResponse(**r) for r in json.loads(FIXTURE.read_text())]


def normalize(items=None):
    return CricbuzzV2PlayerNormalizer("8583").normalize_bundle(*(items or responses()))


def groups(snapshot, name):
    return next(g["rows"] for g in snapshot.groups if g["table"] == name)


def test_observed_career_totals_and_unknowns():
    snapshot = normalize()
    rows = {
        r["format_id"]["code"]: r for r in groups(snapshot, "career_stats_snapshots")
    }
    assert set(rows) == {"TEST", "ODI", "INTERNATIONAL_T20"}
    assert rows["TEST"]["runs"] == 3993
    assert rows["TEST"]["dismissals"] == 103
    assert rows["TEST"]["legal_balls_bowled"] == 96
    assert rows["ODI"]["reported_bowling_average"] is None
    assert rows["INTERNATIONAL_T20"]["reported_economy"] is None
    assert all("catches" not in r and "stumpings" not in r for r in rows.values())
    assert groups(snapshot, "players")[0]["bowling_style"] == "Right-arm medium"


@pytest.mark.parametrize(
    "case",
    [
        "mock",
        "wrong_player",
        "wrong_url",
        "scope",
        "width",
        "duplicate_label",
        "notouts",
        "nan",
        "stale_bundle",
        "unknown_format",
    ],
)
def test_untrusted_or_inconsistent_bundles_rejected(case):
    items = responses()
    if case == "mock":
        items[1] = replace(items[1], is_mock=True)
    elif case == "wrong_player":
        items[0].data["id"] = "9582"
    elif case == "wrong_url":
        items[2].data["appIndex"]["webURL"] = "/profiles/999/x"
    elif case == "scope":
        items[2].data["values"][0]["values"][1] = "67"
    elif case == "width":
        items[1].data["values"][0]["values"].pop()
    elif case == "duplicate_label":
        items[1].data["values"].append(items[1].data["values"][0])
    elif case == "notouts":
        next(r for r in items[1].data["values"] if r["values"][0] == "Not Out")[
            "values"
        ][1] = "999"
    elif case == "nan":
        next(r for r in items[1].data["values"] if r["values"][0] == "Average")[
            "values"
        ][1] = "nan"
    elif case == "stale_bundle":
        items[0] = replace(items[0], fetched_at="2026-10-21T00:00:00Z")
    else:
        items[1].data["headers"][1] = "Mystery"
    with pytest.raises(APIError):
        normalize(items)


@pytest.fixture
def database(tmp_path):
    settings = replace(
        load_settings(environ={}),
        data_mode="live",
        database_path=tmp_path / "players.db",
    )
    initialize_database(settings)
    db = Database(settings)
    yield db
    db.close()


def test_real_capture_roundtrip_and_duplicate(database):
    service = IngestionService(database)
    snap = normalize()
    assert service.ingest(snap).status == "committed"
    assert service.ingest(snap).status == "duplicate"
    reader = PlayerStatsService(database)
    assert reader.latest_career("TEST")[0]["runs"] == 3993
    with database.transaction() as c:
        pid = c.exec_driver_sql("SELECT player_id FROM players").scalar_one()
        assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    assert reader.profile(pid)["role"] == "Batsman"


class Client:
    contract = SimpleNamespace(provider="cricketapilive-cricbuzz-cricket", version="v2")
    policy = SimpleNamespace(min_interval=2)

    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def get(self, operation, **kwargs):
        self.calls.append(operation)
        if operation == self.fail:
            raise APIError("timeout", "Timeout")
        return next(r for r in responses() if r.operation == operation)


def test_service_fetches_before_one_atomic_import(database):
    client = Client()
    pauses = []
    result = PlayerStatsService(database, client).refresh_player(
        "8583", pause=pauses.append
    )
    assert result["status"] == "committed"
    assert client.calls == ["player_profile", "player_batting", "player_bowling"]
    assert pauses == [2, 2]
    assert len(result["subrequests"]) == 3


def test_failure_preserves_existing_career(database):
    service = IngestionService(database)
    service.ingest(normalize())
    with pytest.raises(APIError):
        PlayerStatsService(database, Client("player_bowling")).refresh_player(
            "8583", pause=lambda _: None
        )
    with database.transaction() as c:
        assert (
            c.exec_driver_sql("SELECT COUNT(*) FROM import_batches").scalar_one() == 1
        )
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM career_stats_snapshots"
            ).scalar_one()
            == 3
        )


def test_cli_missing_target_and_invalid_id_spend_no_quota(tmp_path, monkeypatch):
    import api.cli as cli
    from utils.db_connection import DatabaseError

    def forbidden():
        raise AssertionError("Credentials loaded before local checks")

    monkeypatch.setattr(cli, "load_api_settings", forbidden)
    with pytest.raises(ValueError):
        cli.sync_player(tmp_path / "missing.db", "0")
    with pytest.raises(DatabaseError):
        cli.sync_player(tmp_path / "missing.db", "8583")


def test_configured_career_routes_reject_series_filters():

    path = Path(__file__).parents[1] / "api/contracts/cricketapilive_v2.json"
    # Manifest loading is covered elsewhere; inspect the production allowlist too.
    contract = json.loads(path.read_text())
    assert contract["endpoints"]["player_batting"]["optional_query"] == []
    assert contract["endpoints"]["player_bowling"]["optional_query"] == []
