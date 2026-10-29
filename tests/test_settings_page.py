"""Safe diagnostics, session display preferences and six-page navigation."""

import importlib
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from api.client import APIError, HTTPPolicy
from config import PROJECT_ROOT
from services.settings_status import api_readiness, database_health


def page(settings, monkeypatch):
    monkeypatch.setattr("ui.settings.load_settings", lambda: settings)
    monkeypatch.setattr("ui.settings.api_readiness", lambda: {"configured": False})
    return AppTest.from_file(
        str(PROJECT_ROOT / "pages/06_Settings.py"), default_timeout=15
    ).run()


def test_health_is_readonly_and_missing_file_not_created(settings):
    before = database_health(settings)
    assert before["available"] and before["players"] == 12
    assert database_health(settings)["revision"] == before["revision"]
    path = settings.database_path.parent / "missing.db"
    assert database_health(replace(settings, database_path=path)) == {
        "available": False
    }
    assert not path.exists()


def test_mode_mismatch_is_unavailable(settings):
    assert not database_health(replace(settings, data_mode="live"))["available"]


def test_api_summary_never_returns_key_or_url():
    value = SimpleNamespace(
        api_key="secret-marker",
        contract=SimpleNamespace(
            provider="test-provider", version="v2", base_url="private-url"
        ),
        policy=HTTPPolicy(),
    )
    result = api_readiness(lambda: value)
    assert result["configured"]
    assert "secret-marker" not in str(result) and "private-url" not in str(result)

    def fail():
        raise APIError("configuration", "secret-marker")

    assert api_readiness(fail) == {"configured": False}


def test_settings_page_readonly_no_network_and_timezone_apply_reset(
    settings, monkeypatch
):
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("No HTTP")
    ) as network:
        at = page(replace(settings, access_mode="public_readonly"), monkeypatch)
        assert not at.exception
        at.selectbox(key="settings_timezone").select("UTC")
        at.button(
            key="FormSubmitter:settings_display-Apply for this session"
        ).click().run()
        assert at.session_state["display_timezone_override"] == "UTC"
        assert any("Effective timezone: UTC" in x.value for x in at.caption)
        at.button(
            key="FormSubmitter:settings_display-Reset to configured timezone"
        ).click().run()
        assert "display_timezone_override" not in at.session_state
        assert not at.exception and not network.called


def test_timezone_is_applied_on_home_rerun(settings, monkeypatch):
    monkeypatch.setattr("ui.home.load_settings", lambda: settings)
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/01_Home.py"), default_timeout=15)
    at.session_state["display_timezone_override"] = "UTC"
    at.run()
    assert not at.exception
    assert any("Display timezone: UTC" in x.value for x in at.caption)
    at.session_state["display_timezone_override"] = "invalid/timezone"
    at.run()
    assert not at.exception
    assert any("Display timezone: Asia/Kolkata" in x.value for x in at.caption)


def test_settings_missing_target_still_explains_api_status(
    settings, monkeypatch, tmp_path
):
    path = tmp_path / "missing.db"
    at = page(replace(settings, database_path=path), monkeypatch)
    assert not at.exception and at.warning
    assert any("API configuration is incomplete" in x.value for x in at.info)
    assert not path.exists()


def test_configured_api_status_does_not_expose_secret(settings, monkeypatch):
    monkeypatch.setattr("ui.settings.load_settings", lambda: settings)
    readiness = {
        "configured": True,
        "provider": "fixture",
        "version": "v2",
        "connect_timeout": 3,
        "read_timeout": 10,
        "max_attempts": 1,
        "operation_budget": 20,
        "minimum_interval": 2,
    }
    monkeypatch.setattr("ui.settings.api_readiness", lambda: readiness)
    at = AppTest.from_file(
        str(PROJECT_ROOT / "pages/06_Settings.py"), default_timeout=15
    ).run()
    assert not at.exception
    assert any("contract are configured" in x.value for x in at.success)
    assert any("does not verify the key" in x.value for x in at.caption)


def test_all_six_routes_render_without_api_calls_or_writes(
    settings, monkeypatch, database
):
    for name in (
        "home",
        "live_matches",
        "top_players",
        "analytics",
        "crud",
        "settings",
    ):
        module = importlib.import_module("ui." + name)
        monkeypatch.setattr(module, "load_settings", lambda: settings)
    monkeypatch.setattr("ui.settings.api_readiness", lambda: {"configured": False})
    before = database_health(settings)["revision"]
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("No implicit HTTP")
    ) as network:
        at = AppTest.from_file(str(PROJECT_ROOT / "main.py"), default_timeout=15).run()
        for filename in (
            "02_Live_Matches",
            "03_Top_Players",
            "04_Analytics",
            "05_CRUD",
            "06_Settings",
            "01_Home",
        ):
            at.switch_page("pages/" + filename + ".py").run()
            assert not at.exception, filename
        assert not network.called
    assert database_health(settings)["revision"] == before
