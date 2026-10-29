"""Cross-module journeys on temporary databases, including rollback and visibility."""

import json
from dataclasses import replace
from datetime import datetime, timedelta

import pytest
import requests

from api.adapter import decode_snapshot
from config import PROJECT_ROOT
from database.initialize import initialize_database
from services._crud import OwnershipError
from services.analytics import AnalyticsService
from services.ingestion import IngestionService
from services.match_stats import MatchStatsService
from services.overview import OverviewService
from services.players import PlayerService
from services.top_players import TopPlayersService
from utils.charts import ranking_bar
from utils.db_connection import Database


def test_profile_statistic_lifecycle_reaches_analytics_and_overview(database):
    players = PlayerService(database)
    stats = MatchStatsService(database)
    analytics = AnalyticsService(database)
    baseline = OverviewService(database).read()
    player = players.create({"full_name": "Journey player"})
    pid = player["player_id"]
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO match_players(match_id,player_id,team_id,participation) VALUES(1,?,1,'observed')",
            (pid,),
        )
    record = stats.create(
        "batting", 11, pid, 1, 1, {"runs": 20, "balls_faced": 10, "is_dismissed": 0}
    )
    record = stats.update("batting", 11, pid, record["version"], {"runs": 30})
    result = analytics.run_custom(
        f"SELECT runs FROM v_active_batting WHERE player_id={pid}"
    )
    assert result["rows"] == [[30]]
    assert OverviewService(database).read()["players"] == baseline["players"] + 1
    player = players.delete(pid, player["version"])
    assert (
        analytics.run_custom(
            f"SELECT runs FROM v_active_batting WHERE player_id={pid}"
        )["rows"]
        == []
    )
    assert OverviewService(database).read()["players"] == baseline["players"]
    players.restore(pid, player["version"])
    assert analytics.run_custom(
        f"SELECT runs FROM v_active_batting WHERE player_id={pid}"
    )["rows"] == [[30]]
    record = stats.delete("batting", 11, pid, record["version"])
    assert stats.list("batting", pid) == []
    stats.restore("batting", 11, pid, record["version"])
    assert stats.list("batting", pid)[0]["runs"] == 30
    with database.transaction() as c:
        assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []


def test_import_to_ranking_chart_and_profile_tombstone_visibility(settings, tmp_path):
    settings = replace(settings, database_path=tmp_path / "journey.db")
    initialize_database(settings)
    database = Database(settings)
    try:
        payload = json.loads(
            (PROJECT_ROOT / "tests/fixtures/normalized_match.json").read_text()
        )
        snapshot = decode_snapshot(payload)
        importer = IngestionService(database)
        first = importer.ingest(snapshot)
        assert first.status == "committed"
        baseline = OverviewService(database).read()["revision"]
        assert importer.ingest(snapshot).status == "duplicate"
        assert OverviewService(database).read()["revision"] == baseline
        service = TopPlayersService(database)
        catalog = service.catalog()[0]
        source, fmt = catalog["source_id"], catalog["format_id"]
        rows = service.leaders(source, fmt, "Most runs")["rows"]
        assert rows
        figure = ranking_bar(rows, "Most runs", "SYNTHETIC integration fixture")
        assert list(figure.data[0].x) == [r["ranking_value"] for r in rows]
        pid = rows[0]["player_id"]
        players = PlayerService(database)
        profile = players.get(pid)
        with pytest.raises(OwnershipError):
            players.delete(pid, profile["version"])
        deleted = players.delete(pid, profile["version"], override=True)
        payload["metadata"]["fetched_at"] = (
            datetime.fromisoformat(
                payload["metadata"]["fetched_at"].replace("Z", "+00:00")
            )
            + timedelta(days=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert importer.ingest(decode_snapshot(payload)).status == "committed"
        assert pid not in [
            r["player_id"] for r in service.leaders(source, fmt, "Most runs")["rows"]
        ]
        players.restore(pid, deleted["version"])
        assert pid in [
            r["player_id"] for r in service.leaders(source, fmt, "Most runs")["rows"]
        ]
        with database.transaction() as c:
            assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
    finally:
        database.close()


def test_default_test_guard_blocks_unmocked_requests():
    with pytest.raises(AssertionError, match="Real HTTP is disabled"):
        requests.get("https://example.invalid", timeout=1)
