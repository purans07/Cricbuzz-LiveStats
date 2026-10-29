"""Offline series-contract, scoped normalization and CLI target regression checks."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from api.cli import live_settings
from api.client import APIError, APIResponse
from api.series import CricbuzzV2SeriesNormalizer
from config import load_settings


def series_response():
    """Replay only the captured response body, without private request headers."""
    return APIResponse(
        json.loads(
            (
                Path(__file__).parent / "fixtures/cricbuzz_v2_series11595_capture.json"
            ).read_text()
        ),
        "cricketapilive-cricbuzz-cricket",
        "v2",
        "series_matches",
        "2026-10-29T07:04:06Z",
        False,
        {},
    )


def test_series_mapping_preserves_identity_scope_and_no_ads():
    snapshot = CricbuzzV2SeriesNormalizer("11595", "International").normalize(
        series_response()
    )
    groups = {g["table"]: g["rows"] for g in snapshot.groups}
    assert snapshot.capability == "series_matches" and snapshot.resource_key == "11595"
    assert snapshot.origin == "provider" and snapshot.completeness == "partial"
    assert len(groups["matches"]) == 7
    assert {r["external_id"] for r in groups["series"]} == {"11595"}
    assert {r["code"] for r in groups["formats"]} == {
        "TEST",
        "ODI",
        "INTERNATIONAL_WARMUP_TEST",
    }


@pytest.mark.parametrize(
    "case",
    [
        "mock",
        "wrong_operation",
        "wrong_series",
        "unknown_wrapper",
        "empty",
        "duplicate",
    ],
)
def test_series_rejects_mismatched_or_ambiguous_response(case):
    response = series_response()
    if case == "mock":
        response = replace(response, is_mock=True)
    elif case == "wrong_operation":
        response = replace(response, operation="live_matches")
    elif case == "wrong_series":
        response.data["matchDetails"][0]["matchDetailsMap"]["seriesId"] = 999
    elif case == "unknown_wrapper":
        response.data["matchDetails"].append({"unexpected": {}})
    elif case == "empty":
        response.data["matchDetails"] = []
    else:
        response.data["matchDetails"].append(response.data["matchDetails"][0])
    with pytest.raises(APIError):
        CricbuzzV2SeriesNormalizer("11595", "International").normalize(response)


def test_series_requires_reviewed_scope_and_cli_file_target_clears_server(
    monkeypatch, tmp_path
):
    with pytest.raises(ValueError):
        CricbuzzV2SeriesNormalizer("11595", "guess")
    server = replace(
        load_settings(environ={}),
        database_url="postgresql+psycopg://writer:test@localhost/test",
        read_database_url="postgresql+psycopg://reader:test@localhost/test",
    )
    monkeypatch.setattr("api.cli.load_settings", lambda: server)
    settings = live_settings(tmp_path / "live.db")
    assert settings.database_url is None and settings.read_database_url is None
    assert (
        settings.data_mode == "live" and settings.database_path == tmp_path / "live.db"
    )
