"""Public-demo bootstrap policy and real Streamlit entry point on isolated data."""

from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from config import PROJECT_ROOT
from database.initialize import initialize_database
from deployment.public_demo import prepare_public_demo
from services.overview import OverviewService
from utils.db_connection import Database, DatabaseError


def env(path, **extra):
    return {
        "DATABASE_URL": "sqlite:///" + str(path),
        "DATA_MODE": "sample",
        "APP_ACCESS_MODE": "public_readonly",
        **extra,
    }


def test_public_bootstrap_is_idempotent_and_disables_writes(tmp_path):
    path = tmp_path / "demo.db"
    settings = prepare_public_demo(env(path))
    before = path.read_bytes()
    assert prepare_public_demo(env(path)) == settings
    assert path.read_bytes() == before
    database = Database(settings)
    try:
        assert OverviewService(database).read()["players"] == 12
        with pytest.raises(DatabaseError):
            with database.transaction(write=True):
                pass
    finally:
        database.close()


@pytest.mark.parametrize("extra", [{"DATA_MODE": "live"}, {"APP_ACCESS_MODE": "local"}])
def test_public_entry_refuses_unsafe_modes_before_creation(tmp_path, extra):
    path = tmp_path / "refused.db"
    with pytest.raises(DatabaseError):
        prepare_public_demo(env(path, **extra))
    assert not path.exists()


def test_existing_incompatible_file_is_never_replaced(settings, tmp_path):
    path = tmp_path / "existing.db"
    initialize_database(replace(settings, data_mode="live", database_path=path))
    before = path.read_bytes()
    with pytest.raises(DatabaseError):
        prepare_public_demo(env(path))
    assert path.read_bytes() == before


def test_cloud_entry_renders_readonly_home_and_other_routes(tmp_path, monkeypatch):
    path = tmp_path / "cloud.db"
    for key, value in env(path).items():
        monkeypatch.setenv(key, value)
    at = AppTest.from_file(str(PROJECT_ROOT / "cloud_app.py"), default_timeout=20).run()
    assert not at.exception and at.metric[0].value == "72"
    assert any("SAMPLE DATA" in x.value for x in at.info)
    at.switch_page("pages/05_CRUD.py").run()
    assert not at.exception and not at.form
    at.switch_page("pages/04_Analytics.py").run()
    at.radio(key="analytics_workspace").set_value("Custom SQL").run()
    assert not at.exception and not at.text_area


def test_cloud_entry_stops_with_safe_message_for_wrong_mode(tmp_path, monkeypatch):
    path = tmp_path / "refused.db"
    for key, value in env(path, DATA_MODE="live").items():
        monkeypatch.setenv(key, value)
    at = AppTest.from_file(str(PROJECT_ROOT / "cloud_app.py"), default_timeout=20).run()
    assert not at.exception and at.error and not path.exists()
