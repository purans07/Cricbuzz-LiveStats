"""Real-record public bootstrap: no HTTP, no public writes, honest source labels."""

import pytest
from streamlit.testing.v1 import AppTest

from config import PROJECT_ROOT
from deployment.public_provider import prepare_public_provider
from services.overview import OverviewService
from utils.db_connection import Database, DatabaseError


def test_provider_bootstrap_preserves_records_and_blocks_public_writes(tmp_path):
    path = tmp_path / "provider.db"
    settings = prepare_public_provider(database_path=path)
    db = Database(settings)
    try:
        first = OverviewService(db).read()
        assert first["mode"] == "live" and first["matches"] >= 64
        assert first["players"] >= 2
        with pytest.raises(DatabaseError):
            with db.transaction(write=True):
                pass
        prepare_public_provider(database_path=path)
        assert OverviewService(db).read() == first
    finally:
        db.close()


def test_absent_public_snapshots_do_not_create_database(tmp_path):
    with pytest.raises(ValueError):
        prepare_public_provider(tmp_path, tmp_path / "absent.db")
    assert not (tmp_path / "absent.db").exists()


def test_public_provider_cloud_routes_have_real_labels_and_no_admin_forms(
    tmp_path, monkeypatch
):
    settings = prepare_public_provider(database_path=tmp_path / "public.db")
    monkeypatch.setenv("PUBLIC_DATA_MODE", "live")
    monkeypatch.setattr(
        "deployment.public_provider.prepare_public_provider", lambda: settings
    )
    at = AppTest.from_file(str(PROJECT_ROOT / "cloud_app.py"), default_timeout=30).run()
    assert not at.exception
    assert any("Saved provider records" in x.value for x in at.info)
    assert int(at.metric[0].value) >= 64
    at.switch_page("pages/03_Top_Players.py").run()
    assert not at.exception
    assert any("SAVED PROVIDER DATA" in x.value for x in at.info)
    at.switch_page("pages/05_CRUD.py").run()
    assert not at.exception and not at.form


def test_scorecard_budget_and_completed_cache():
    from deployment.public_provider import PUBLIC_DATA, scorecard_candidates

    selected = scorecard_candidates(PUBLIC_DATA)
    assert len(selected) <= 2
    assert "175081" not in {mid for mid, _ in selected}
    assert scorecard_candidates(PUBLIC_DATA, limit=0) == []
    with pytest.raises(ValueError):
        scorecard_candidates(PUBLIC_DATA, limit=3)


def test_captured_public_scorecard_has_batting_and_bowling_details(tmp_path):
    from sqlalchemy import text

    from services.live_matches import LiveMatchService

    settings = prepare_public_provider(database_path=tmp_path / "details.db")
    db = Database(settings)
    try:
        with db.transaction() as connection:
            mid = connection.execute(
                text("SELECT match_id FROM matches WHERE external_id='175081'")
            ).scalar_one()
        innings = LiveMatchService(db).scorecard(mid)
        assert len(innings) == 2
        assert all(inning["batting"] and inning["bowling"] for inning in innings)
        assert sum(len(inning["batting"]) for inning in innings) == 10
        assert sum(len(inning["bowling"]) for inning in innings) == 10
    finally:
        db.close()
