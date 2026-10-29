"""Home overview provenance, database failure states and Streamlit rendering."""

from dataclasses import replace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from config import PROJECT_ROOT, ConfigurationError
from services.overview import OverviewService


def app(settings, monkeypatch):
    monkeypatch.setattr("ui.home.load_settings", lambda: settings)
    return AppTest.from_file(str(PROJECT_ROOT / "main.py"), default_timeout=15).run()


def test_overview_is_read_only_and_counts_active_players(database):
    before = OverviewService(database).read()
    assert {k: before[k] for k in ("matches", "players", "teams", "venues")} == {
        "matches": 72,
        "players": 12,
        "teams": 2,
        "venues": 2,
    }
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    after = OverviewService(database).read()
    assert after["players"] == 11
    assert (
        OverviewService(database).read()["revision"]
        == after["revision"]
        == before["revision"] + 1
    )


def test_no_committed_import_has_no_timestamp(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE import_batches SET status='failed'")
    result = OverviewService(database).read()
    assert result["latest_import"] is None
    assert result["partial_imports"] == 0


def test_home_renders_and_reload_makes_no_http_calls(settings, monkeypatch):
    with patch(
        "requests.sessions.Session.send",
        side_effect=AssertionError("Home must not fetch"),
    ) as network:
        at = app(settings, monkeypatch)
        assert not at.exception
        assert [m.value for m in at.metric] == ["72", "12", "2", "2"]
        assert any("SAMPLE DATA" in x.value for x in at.info)
        assert len(at.expander) == 0
        at.button(key="reload_overview").click().run()
        assert not at.exception
        assert not network.called


def test_home_rereads_changes_instead_of_stale_cached_counts(
    settings, database, monkeypatch
):
    at = app(settings, monkeypatch)
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    at.button(key="reload_overview").click().run()
    assert at.metric[1].value == "11"
    assert not at.exception


def test_live_label_does_not_claim_current_fetch(settings, database, monkeypatch):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE dataset_state SET mode='live'")
    at = app(replace(settings, data_mode="live"), monkeypatch)
    assert not at.exception
    assert any("Saved provider records" in x.value for x in at.info)
    assert not any("SAMPLE DATA" in x.value for x in at.info)


def test_missing_database_keeps_navigation_and_does_not_create_file(
    settings, monkeypatch, tmp_path
):
    path = tmp_path / "not_initialized.db"
    at = app(replace(settings, database_path=path), monkeypatch)
    assert not at.exception and at.warning
    assert not at.metric
    assert len(at.expander) == 0
    assert not path.exists()


def test_configuration_error_is_redacted_and_navigation_remains(monkeypatch):
    def fail():
        raise ConfigurationError("private-marker-must-not-appear")

    monkeypatch.setattr("ui.home.load_settings", fail)
    at = AppTest.from_file(str(PROJECT_ROOT / "main.py"), default_timeout=15).run()
    assert not at.exception and at.error
    assert "private-marker" not in at.error[0].value
    assert len(at.expander) == 0


def test_public_readonly_home_works(settings, monkeypatch):
    at = app(replace(settings, access_mode="public_readonly"), monkeypatch)
    assert not at.exception
    assert any("SAMPLE DATA" in message.value for message in at.info)
