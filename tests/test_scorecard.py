"""Offline verification against the user's regular scorecard capture."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from api.client import APIError, APIResponse
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer
from api.scorecard import CricbuzzV2ScorecardNormalizer
from config import load_settings
from database.initialize import initialize_database
from services.ingestion import IngestionService
from utils.db_connection import Database

FIXTURES = Path(__file__).parent / "fixtures"


def response():
    return APIResponse(
        json.loads((FIXTURES / "cricbuzz_v2_scorecard_user_capture.json").read_text()),
        "cricketapilive-cricbuzz-cricket",
        "v2",
        "match_scorecard",
        "2026-10-22T07:25:00Z",
        False,
        {},
    )


def adapter():
    return CricbuzzV2ScorecardNormalizer(
        "147931", {"South Africa": "11", "Australia": "4"}
    )


def rows(snapshot, table):
    return next(g["rows"] for g in snapshot.groups if g["table"] == table)


def test_real_capture_dnb_followon_and_bowling_units():
    snap = adapter().normalize(response())
    assert len(rows(snap, "players")) == 22
    assert len(rows(snap, "batting_performances")) == 27
    assert len(rows(snap, "bowling_performances")) == 19
    assert [i["batting_team_id"]["external_id"] for i in rows(snap, "innings")] == [
        "11",
        "4",
        "4",
    ]
    starc = next(
        b
        for b in rows(snap, "bowling_performances")
        if b["player_id"]["external_id"] == "7710"
    )
    assert (
        starc["legal_balls"] == 145
    )  # 24.1 overs; never the provider's encoded 'balls'.
    assert [i["legal_balls"] for i in rows(snap, "innings")] == [763, 255, 324]


@pytest.mark.parametrize(
    "case",
    ["wrong_match", "mock", "duplicate", "unknown_team", "opposite_team", "bad_overs"],
)
def test_malformed_or_wrong_provenance_rejected(case):
    r = response()
    if case == "wrong_match":
        r.data["appindex"]["weburl"] = "/live-cricket-scorecard/40381/x"
    elif case == "mock":
        r = replace(r, is_mock=True)
    elif case == "duplicate":
        r.data["scorecard"].append(r.data["scorecard"][0])
    elif case == "unknown_team":
        r.data["scorecard"][0]["batteamname"] = "Unknown"
    elif case == "opposite_team":
        r.data["scorecard"][1]["batsman"][0]["id"] = 9582
        r.data["scorecard"][1]["batsman"][0]["name"] = "Aiden Markram"
    else:
        r.data["scorecard"][0]["bowler"][0]["overs"] = "24.9"
    with pytest.raises(APIError):
        adapter().normalize(r)


def test_atomic_import_duplicate_replay_and_team_foreign_keys(tmp_path):
    settings = replace(
        load_settings(environ={}), data_mode="live", database_path=tmp_path / "live.db"
    )
    initialize_database(settings)
    db = Database(settings)
    try:
        service = IngestionService(db)
        listing = replace(
            response(),
            operation="live_matches",
            fetched_at="2026-10-21T17:40:39Z",
            data=json.loads(
                (FIXTURES / "cricbuzz_v2_live_user_capture.json").read_text()
            ),
        )
        service.ingest(CricbuzzV2MatchListNormalizer().normalize(listing))
        snap = adapter().normalize(response())
        assert service.ingest(snap).status == "committed"
        assert service.ingest(snap).status == "duplicate"
        with db.transaction() as conn:
            assert (
                conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM batting_performances"
                ).scalar_one()
                == 27
            )
            assert (
                conn.exec_driver_sql(
                    "SELECT COUNT(*) FROM bowling_performances"
                ).scalar_one()
                == 19
            )
            assert conn.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        db.close()


@pytest.mark.parametrize("description", ["retired hurt", "retd hurt"])
def test_retired_hurt_alias_is_observed_but_not_a_dismissal(description):
    r = response()
    batter = r.data["scorecard"][0]["batsman"][0]
    batter["outdec"] = description
    snap = adapter().normalize(r)
    record = next(
        b
        for b in rows(snap, "batting_performances")
        if b["innings_id"]["innings_number"] == 1
        and b["player_id"]["external_id"] == str(batter["id"])
    )
    assert record["is_dismissed"] == 0
    assert record["dismissal_text"] == description
    assert record["runs"] == batter["runs"]
    assert record["balls_faced"] == batter["balls"]
