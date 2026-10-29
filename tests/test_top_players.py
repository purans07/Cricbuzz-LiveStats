"""Latest source/format ranks, missing ratios, ties and actual Streamlit UI."""

import json
from dataclasses import replace
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from api.client import APIResponse
from api.players import CricbuzzV2PlayerNormalizer
from config import PROJECT_ROOT
from database.initialize import initialize_database
from services.ingestion import IngestionService
from services.top_players import TopPlayersService
from utils.db_connection import Database


def chosen(db, metric="Most runs", **params):
    service = TopPlayersService(db)
    cat = service.catalog()
    row = next(r for r in cat if r["format_code"] == "ODI")
    return service.leaders(row["source_id"], row["format_id"], metric, **params)


def page(settings, monkeypatch):
    monkeypatch.setattr("ui.top_players.load_settings", lambda: settings)
    return AppTest.from_file(
        str(PROJECT_ROOT / "pages/03_Top_Players.py"), default_timeout=15
    ).run()


def test_latest_snapshots_ranked_once_per_player_not_summed(database):
    result = chosen(database)
    assert result["coverage"]["eligible_players"] == 12
    assert len(result["rows"]) == 10
    assert result["rows"][0]["player_name"] == "Sample Player 12"
    assert all(r["fetched_at"] == "2026-10-01T00:00:00Z" for r in result["rows"])
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE import_batches SET status='failed' WHERE batch_id=2")
    assert all(
        r["fetched_at"] == "2026-09-01T00:00:00Z" for r in chosen(database)["rows"]
    )


def test_unknown_totals_excluded_known_zero_retained(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=NULL WHERE batch_id=2 AND format_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=0 WHERE batch_id=2 AND format_id=2 AND player_id=1"
        )
    result = chosen(database)
    assert result["coverage"]["eligible_players"] == 12
    assert result["coverage"]["ranked_players"] == 1
    assert result["rows"][0]["runs"] == 0


def test_zero_denominator_undefined_unknown_denominator_reported_fallback(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=0,reported_batting_average=999 WHERE batch_id=2 AND format_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=NULL,reported_batting_average=33 WHERE batch_id=2 AND format_id=2 AND player_id=1"
        )
    rows = chosen(database, "Batting average")["rows"]
    assert len(rows) == 1 and rows[0]["batting_average"] == 33


def test_bowling_order_is_ascending_and_zero_wickets_excluded(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET wickets=0 WHERE batch_id=2 AND format_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET wickets=10,runs_conceded=100 WHERE batch_id=2 AND format_id=2 AND player_id=1"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET wickets=10,runs_conceded=200 WHERE batch_id=2 AND format_id=2 AND player_id=2"
        )
    rows = chosen(database, "Bowling average")["rows"]
    assert [r["player_id"] for r in rows] == [1, 2]
    assert [r["bowling_average"] for r in rows] == [10, 20]


def test_dense_ties_and_limits_use_stable_ids(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET full_name='Same name'")
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=100 WHERE batch_id=2 AND format_id=2"
        )
    rows = chosen(database, limit=3)["rows"]
    assert [r["player_id"] for r in rows] == [1, 2, 3]
    assert all(r["rank"] == 1 for r in rows)


def test_match_filter_unknown_count_and_deleted_profiles(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET matches_played=NULL WHERE batch_id=2 AND player_id=1"
        )
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=2")
    assert chosen(database)["coverage"]["eligible_players"] == 11
    assert chosen(database, minimum_matches=1)["coverage"]["eligible_players"] == 10
    assert chosen(database, minimum_matches=100000)["rows"] == []


def test_source_and_format_isolation(database):
    service = TopPlayersService(database)
    row = next(r for r in service.catalog() if r["format_code"] == "ODI")
    assert service.leaders(999, row["format_id"], "Most runs")["rows"] == []
    assert service.leaders(row["source_id"], 999, "Most runs")["rows"] == []
    with pytest.raises(ValueError):
        service.leaders(
            row["source_id"], row["format_id"], "runs DESC; DROP TABLE players"
        )
    with pytest.raises(ValueError):
        service.leaders(True, row["format_id"], "Most runs")
    with pytest.raises(ValueError):
        chosen(database, limit=101)


def test_ui_filter_reruns_never_fetch_and_profile_renders(settings, monkeypatch):
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("Unexpected HTTP")
    ) as network:
        at = page(settings, monkeypatch)
        assert not at.exception and at.dataframe
        assert any("SAMPLE DATA" in x.value for x in at.info)
        assert any(e.label == "Player profile and career scope" for e in at.expander)
        at.selectbox(key="top_metric").select("Most wickets").run()
        at.number_input(key="top_minimum").set_value(100000).run()
        assert not at.exception and any("No known values" in x.value for x in at.info)
        assert not network.called


def test_ui_reload_reflects_changed_records(settings, database, monkeypatch):
    at = page(settings, monkeypatch)
    assert at.metric[0].value == "12"
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    at.button(key="reload_top_players").click().run()
    assert at.metric[0].value == "11" and not at.exception


def test_no_careers_empty_state_and_missing_database(
    settings, database, monkeypatch, tmp_path
):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE import_batches SET status='failed'")
    at = page(settings, monkeypatch)
    assert not at.exception and any("No career statistics" in x.value for x in at.info)
    path = tmp_path / "absent.db"
    at = page(replace(settings, database_path=path), monkeypatch)
    assert at.warning and not at.exception and not path.exists()


def test_captured_provider_career_renders_limited_coverage(
    settings, tmp_path, monkeypatch
):
    settings = replace(
        settings,
        data_mode="live",
        access_mode="local",
        database_path=tmp_path / "live.db",
    )
    initialize_database(settings)
    db = Database(settings)
    try:
        payload = json.loads(
            (PROJECT_ROOT / "tests/fixtures/cricbuzz_v2_player_8583.json").read_text()
        )
        response = [APIResponse(**r) for r in payload]
        IngestionService(db).ingest(
            CricbuzzV2PlayerNormalizer("8583").normalize_bundle(*response)
        )
        result = chosen(db)
        assert len(result["rows"]) == 1 and result["rows"][0]["runs"] == 2168
        at = page(replace(settings, access_mode="public_readonly"), monkeypatch)
        assert not at.exception and at.dataframe
        assert any("Limited player coverage" in x.value for x in at.warning)
        assert at.metric[0].value == "1"
    finally:
        db.close()
