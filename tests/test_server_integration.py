"""Opt-in acceptance on disposable localhost servers; no provider HTTP requests."""

import json
import math
import os
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from api.adapter import decode_snapshot
from config import load_settings
from database.server import initialize_server
from services.analytics import QUESTIONS, AnalyticsError, AnalyticsService
from services.ingestion import IngestionService
from services.match_stats import MatchStatsService
from services.players import PlayerService
from services.top_players import TopPlayersService
from utils.db_connection import Database, DatabaseError


@pytest.fixture(scope="module", params=["postgresql", "mysql"])
def server_database(request):
    path = os.environ.get("CRICBUZZ_SERVER_TEST_SETTINGS")
    if not path:
        pytest.skip(
            "Opt-in: requires disposable localhost PostgreSQL/MySQL test schemas."
        )
    values = json.loads(Path(path).read_text())[request.param]
    url = make_url(values["DATABASE_URL"])
    assert (
        url.host == "127.0.0.1"
        and url.port >= 50000
        and url.database.startswith("cricbuzz_test")
    )
    db = Database(load_settings(environ=values))
    yield db
    db.close()


@pytest.mark.parametrize("query", [q.id for q in QUESTIONS])
def test_all_queries_match_sqlite_seed(server_database, database, query):
    expected = AnalyticsService(database).run_saved(
        query, "2026-10-01", "Synthetic training fixture"
    )
    actual = AnalyticsService(server_database).run_saved(
        query, "2026-10-01", "Synthetic training fixture"
    )
    assert expected["columns"] == actual["columns"]
    assert len(expected["rows"]) == len(actual["rows"])
    for a, b in zip(expected["rows"], actual["rows"], strict=True):
        for x, y in zip(a, b, strict=True):
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                assert math.isclose(x, y, rel_tol=1e-5, abs_tol=1e-4)
            else:
                assert x == y


def test_leaderboard_and_profile_stat_lifecycle(server_database):
    db = server_database
    catalog = TopPlayersService(db).catalog()
    chosen = catalog[0]
    assert TopPlayersService(db).leaders(
        chosen["source_id"], chosen["format_id"], "Most runs"
    )["rows"]
    players = PlayerService(db)
    p = players.create({"full_name": "Server lifecycle acceptance"})
    pid = p["player_id"]
    assert players.get(pid)["full_name"] == p["full_name"]
    p = players.update(pid, p["version"], {"full_name": "Server lifecycle edited"})
    with pytest.raises(ValueError):
        players.update(pid, 1, {"full_name": "Stale edit"})
    with db.transaction(write=True) as c:
        inning = c.exec_driver_sql(
            "SELECT innings_id,match_id,batting_team_id FROM innings ORDER BY innings_id LIMIT 1"
        ).first()
        c.execute(
            text(
                "INSERT INTO match_players(match_id,player_id,team_id,participation) VALUES (:m,:p,:t,'observed')"
            ),
            {"m": inning[1], "p": pid, "t": inning[2]},
        )
    stats = MatchStatsService(db)
    row = stats.create(
        "batting",
        inning[0],
        pid,
        inning[1],
        inning[2],
        {"runs": 10, "balls_faced": 12, "is_dismissed": 0},
    )
    row = stats.update("batting", inning[0], pid, row["version"], {"runs": 11})
    assert row["runs"] == 11
    row = stats.delete("batting", inning[0], pid, row["version"])
    assert stats.get("batting", inning[0], pid) is None
    stats.restore("batting", inning[0], pid, row["version"])
    p = players.delete(pid, p["version"])
    assert players.get(pid) is None
    players.restore(pid, p["version"])
    # Reversible test cleanup; working/user databases are never targeted.
    p = players.get(pid)
    players.delete(pid, p["version"])


def test_rollback_readonly_policy_and_restricted_queries(server_database):
    db = server_database
    with db.transaction() as c:
        revision = c.exec_driver_sql(
            "SELECT revision FROM dataset_state WHERE singleton_id=1"
        ).scalar_one()
    with pytest.raises(RuntimeError):
        with db.transaction(write=True) as c:
            c.exec_driver_sql(
                "UPDATE dataset_state SET revision=revision+10 WHERE singleton_id=1"
            )
            raise RuntimeError("intentional acceptance rollback")
    with db.transaction() as c:
        assert (
            c.exec_driver_sql(
                "SELECT revision FROM dataset_state WHERE singleton_id=1"
            ).scalar_one()
            == revision
        )
        with pytest.raises(SQLAlchemyError):
            c.exec_driver_sql("DELETE FROM players WHERE player_id=-1")
    for sql in [
        "DELETE FROM players",
        "SELECT pg_sleep(5)",
        "SELECT * FROM information_schema.tables",
        "SELECT 1; DELETE FROM players",
    ]:
        with pytest.raises(AnalyticsError):
            AnalyticsService(db).run_custom(sql)
    ro = Database(replace(db.settings, access_mode="public_readonly"))
    try:
        with pytest.raises(DatabaseError):
            with ro.transaction(write=True):
                pass
        with pytest.raises(AnalyticsError):
            AnalyticsService(ro).run_custom("SELECT 1")
    finally:
        ro.close()
    with pytest.raises(DatabaseError):
        initialize_server(db.settings, seed_sample=True)


def test_snapshot_import_repeat_is_idempotent(server_database):
    payload = json.loads(
        (Path(__file__).parent / "fixtures/normalized_match.json").read_text()
    )
    snapshot = decode_snapshot(payload, origin="synthetic")
    from contextlib import contextmanager
    from types import SimpleNamespace

    class RollbackProbe(Exception):
        """Discard the synthetic probe after exercising nested import transactions."""

    with pytest.raises(RollbackProbe):
        with server_database.transaction(write=True) as connection:

            @contextmanager
            def transaction(*, write=False):
                """Reuse this probe's real server connection under a savepoint."""
                with connection.begin_nested():
                    yield connection

            probe = SimpleNamespace(
                settings=server_database.settings, transaction=transaction
            )
            importer = IngestionService(probe)
            assert importer.ingest(snapshot).status == "committed"
            assert importer.ingest(snapshot).status == "duplicate"
            raise RollbackProbe


def test_all_six_pages_render_with_server_settings(server_database, monkeypatch):
    """Exercise the real navigation routes against each server without HTTP or writes."""
    import importlib

    from streamlit.testing.v1 import AppTest

    from config import PROJECT_ROOT

    for module in [
        "home",
        "live_matches",
        "top_players",
        "analytics",
        "crud",
        "settings",
    ]:
        monkeypatch.setattr(
            importlib.import_module("ui." + module),
            "load_settings",
            lambda: server_database.settings,
        )
    app = AppTest.from_file(str(PROJECT_ROOT / "main.py"), default_timeout=15).run()
    assert not app.exception
    for path in [
        "pages/02_Live_Matches.py",
        "pages/03_Top_Players.py",
        "pages/04_Analytics.py",
        "pages/05_CRUD.py",
        "pages/06_Settings.py",
    ]:
        app.switch_page(path).run()
        assert not app.exception


def test_head_to_head_venue_variant_matches_sqlite(server_database, database):
    """Check the additional Q22 venue output, beyond the main question registry."""
    expected = AnalyticsService(database).run_saved(
        "Q22", "2026-10-01", venue_breakdown=True
    )
    actual = AnalyticsService(server_database).run_saved(
        "Q22", "2026-10-01", venue_breakdown=True
    )
    assert expected["columns"] == actual["columns"]
    assert len(expected["rows"]) == len(actual["rows"])
    for row_a, row_b in zip(expected["rows"], actual["rows"], strict=True):
        for a, b in zip(row_a, row_b, strict=True):
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                assert math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-4)
            else:
                assert a == b


def test_privileged_reader_credentials_are_rejected(server_database):
    """A distinct URL cannot bypass the actual SELECT-only privilege check."""
    db = Database(
        replace(
            server_database.settings,
            read_database_url=server_database.settings.database_url,
        )
    )
    try:
        with pytest.raises(DatabaseError):
            with db.transaction():
                pass
    finally:
        db.close()
