"""Map the user's supplied body; no live request is made by these tests."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from api.client import APIError, APIResponse
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer, _balls
from config import load_settings
from database.initialize import initialize_database
from services.ingestion import IngestionService
from utils.db_connection import Database

FIXTURE = Path(__file__).parent / "fixtures/cricbuzz_v2_live_user_capture.json"


@pytest.fixture
def response():
    return APIResponse(
        json.loads(FIXTURE.read_text()),
        "cricketapilive-cricbuzz-cricket",
        "v2",
        "live_matches",
        "2026-10-21T17:40:39Z",
        False,
        {},
    )


def group(snapshot, table):
    return next(item["rows"] for item in snapshot.groups if item["table"] == table)


def test_captured_structure_counts_and_ad_skipping(response):
    snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
    assert len(group(snapshot, "matches")) == 9
    assert len(group(snapshot, "series")) == 7
    assert len(group(snapshot, "teams")) == 18
    assert len(group(snapshot, "innings")) == 18
    assert snapshot.completeness == "partial"
    assert snapshot.origin == "provider"
    assert not any(g["table"] == "players" for g in snapshot.groups)


def test_completed_matches_not_dropped_or_results_invented(response):
    matches = group(CricbuzzV2MatchListNormalizer().normalize(response), "matches")
    complete = [m for m in matches if m["status"] == "completed"]
    assert {m["external_id"] for m in complete} == {"163701", "175490"}
    assert all("winner_team_id" not in m and "completed_at" not in m for m in matches)
    assert all("toss_winner_id" not in m for m in matches)
    assert any(m["status_text"] == "Match drawn" for m in matches)


def test_missing_country_capacity_and_format_scope_are_not_guessed(response):
    snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
    assert all(
        "country_id" not in v and "capacity" not in v for v in group(snapshot, "venues")
    )
    formats = {f["code"] for f in group(snapshot, "formats")}
    assert "T20I" not in formats
    assert {"INTERNATIONAL_T20", "LEAGUE_T20", "DOMESTIC_TEST"} <= formats


@pytest.mark.parametrize(
    "value,expected", [(53.6, 324), (49.6, 300), (28.6, 174), (127.1, 763), (42.3, 255)]
)
def test_provider_over_notation(value, expected):
    assert _balls(value) == expected


@pytest.mark.parametrize("value", [53.7, "1.12", -1, True, float("nan")])
def test_invalid_provider_overs(value):
    with pytest.raises(ValueError):
        _balls(value)


def test_millisecond_and_second_timestamps(response):
    snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
    assert snapshot.upstream_updated_at.endswith("Z")
    first = group(snapshot, "matches")[0]
    assert first["starts_at"].startswith("2026-10-")
    assert len(first["starts_at"]) == 20


def test_actual_follow_on_order_is_retained(response):
    snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
    innings = [
        r
        for r in group(snapshot, "innings")
        if r["match_id"]["external_id"] == "147931"
    ]
    assert [
        (r["innings_number"], r["batting_team_id"]["external_id"]) for r in innings
    ] == [(1, "11"), (2, "4"), (3, "4")]


@pytest.mark.parametrize(
    "case",
    ["missing_root", "unknown_wrapper", "bad_overs", "duplicate_match", "wrong_series"],
)
def test_malformed_body_is_rejected(response, case):
    data = response.data
    if case == "missing_root":
        data.pop("typeMatches")
    elif case == "unknown_wrapper":
        data["typeMatches"][0]["seriesMatches"].append({"surprise": {}})
    elif case == "bad_overs":
        data["typeMatches"][0]["seriesMatches"][0]["seriesAdWrapper"]["matches"][0][
            "matchScore"
        ]["team1Score"]["inngs1"]["overs"] = 4.7
    elif case == "duplicate_match":
        matches = data["typeMatches"][0]["seriesMatches"][0]["seriesAdWrapper"][
            "matches"
        ]
        matches.append(matches[0])
    else:
        data["typeMatches"][0]["seriesMatches"][0]["seriesAdWrapper"]["matches"][0][
            "matchInfo"
        ]["seriesId"] = 1
    with pytest.raises(APIError, match="malformed"):
        CricbuzzV2MatchListNormalizer().normalize(response)


def test_mock_and_unsupported_operation_are_rejected(response):
    for changed in (
        replace(response, is_mock=True),
        replace(response, operation="scorecard"),
    ):
        with pytest.raises(APIError, match="provider"):
            CricbuzzV2MatchListNormalizer().normalize(changed)


def test_empty_match_list_is_valid(response):
    snapshot = CricbuzzV2MatchListNormalizer().normalize(
        replace(response, data={"typeMatches": []})
    )
    assert group(snapshot, "matches") == []


def test_captured_list_imports_atomically_without_touching_working_database(
    response, tmp_path
):
    settings = replace(
        load_settings(environ={}),
        data_mode="live",
        database_path=tmp_path / "captured-test.db",
    )
    initialize_database(settings)
    database = Database(settings)
    try:
        snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
        service = IngestionService(database)
        assert service.ingest(snapshot).status == "committed"
        assert service.ingest(snapshot).status == "duplicate"
        with database.transaction() as connection:
            assert (
                connection.exec_driver_sql("SELECT COUNT(*) FROM matches").scalar_one()
                == 9
            )
            assert (
                connection.exec_driver_sql("SELECT COUNT(*) FROM innings").scalar_one()
                == 18
            )
            assert (
                connection.exec_driver_sql("SELECT COUNT(*) FROM players").scalar_one()
                == 0
            )
            assert (
                connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
            )
    finally:
        database.close()


def test_newly_observed_lunch_state_remains_live(response):
    response.data["typeMatches"][0]["seriesMatches"][0]["seriesAdWrapper"]["matches"][
        0
    ]["matchInfo"]["state"] = "Lunch"
    snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
    assert group(snapshot, "matches")[0]["status"] == "live"


def test_warmup_does_not_enter_official_test_format(response):
    info = response.data["typeMatches"][0]["seriesMatches"][0]["seriesAdWrapper"][
        "matches"
    ][0]["matchInfo"]
    info["matchDesc"] = "Warm-up Match"
    snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
    match = group(snapshot, "matches")[0]
    assert match["format_id"]["code"] == "INTERNATIONAL_WARMUP_TEST"
    format_row = next(
        row
        for row in group(snapshot, "formats")
        if row["code"] == "INTERNATIONAL_WARMUP_TEST"
    )
    assert format_row["family"] == "OTHER" and format_row["level"] == "other"


def test_national_team_in_league_wrapper_retains_international_identity(response):
    from copy import deepcopy

    duplicate = deepcopy(response.data["typeMatches"][0])
    duplicate["matchType"] = "League"
    for wrapper in duplicate["seriesMatches"]:
        for match in wrapper.get("seriesAdWrapper", {}).get("matches", []):
            match["matchInfo"]["matchId"] += 1000000
    data = deepcopy(response.data)
    data["typeMatches"].append(duplicate)
    before = group(CricbuzzV2MatchListNormalizer().normalize(response), "teams")
    after = group(
        CricbuzzV2MatchListNormalizer().normalize(replace(response, data=data)), "teams"
    )
    expected = {row["external_id"] for row in before if row["is_international"]}
    assert all(
        row["is_international"] == 1 for row in after if row["external_id"] in expected
    )
