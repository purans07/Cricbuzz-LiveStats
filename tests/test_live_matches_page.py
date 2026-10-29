"""Saved scorecard rendering, no implicit HTTP and guarded refresh integration."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from api.client import APIError, APIResponse, HTTPPolicy, ProviderContract
from config import PROJECT_ROOT
from database.initialize import initialize_database
from services.live_matches import LiveMatchService, RefreshCoordinator
from utils.db_connection import Database


@pytest.fixture
def live_db(settings, tmp_path):
    settings = replace(settings, data_mode="live", database_path=tmp_path / "live.db")
    initialize_database(settings)
    db = Database(settings)
    yield db
    db.close()


def coordinator(*, clock=None, error=None, empty=False):
    contract = ProviderContract(
        "cricketapilive-cricbuzz-cricket", "v2", "https://fixture.example", "X-Test", {}
    )
    calls = []

    class Client:
        def __init__(self, *args, **kwargs):
            self.contract = contract

        def get(self, operation, **kwargs):
            calls.append((operation, kwargs))
            if error:
                raise error
            name = (
                "cricbuzz_v2_live_user_capture.json"
                if operation == "live_matches"
                else "cricbuzz_v2_scorecard_user_capture.json"
            )
            data = json.loads((PROJECT_ROOT / "tests/fixtures" / name).read_text())
            if empty:
                data = {"typeMatches": []}
            return APIResponse(
                data,
                contract.provider,
                contract.version,
                operation,
                "2026-10-28T06:30:44Z",
                False,
                {},
            )

        def close(self):
            calls.append(("closed", {}))

    instance = RefreshCoordinator(
        clock=clock or (lambda: 100),
        settings_loader=lambda: SimpleNamespace(
            contract=contract, api_key="placeholder", policy=HTTPPolicy()
        ),
        client_factory=Client,
    )
    return instance, calls


def page(settings, monkeypatch):
    monkeypatch.setattr("ui.live_matches.load_settings", lambda: settings)
    return AppTest.from_file(
        str(PROJECT_ROOT / "pages/02_Live_Matches.py"), default_timeout=15
    ).run()


def test_saved_match_counts_do_not_multiply_with_innings(database):
    service = LiveMatchService(database)
    assert len(service.matches()) == 72
    innings = service.scorecard(1)
    assert len(innings) == 4
    assert len(innings[0]["batting"]) == 6
    assert len(innings[0]["bowling"]) == 6
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert len(service.scorecard(1)[0]["batting"]) == 5
    assert service.scorecard(999999) == []
    with pytest.raises(ValueError):
        service.scorecard("1")


def test_refresh_imports_captured_list_then_selected_regular_scorecard(live_db):
    clock = [100]
    gate, calls = coordinator(clock=lambda: clock[0])
    result = gate.refresh(live_db)
    assert result["status"] == "committed" and result["match_count"] == 9
    match = next(
        m for m in LiveMatchService(live_db).matches() if m["external_id"] == "147931"
    )
    clock[0] += 31
    assert gate.refresh(live_db, match["match_id"])["status"] == "committed"
    innings = LiveMatchService(live_db).scorecard(match["match_id"])
    assert len(innings) == 3
    assert any(b["player"] == "Temba Bavuma" for i in innings for b in i["batting"])
    assert calls[2][0] == "match_scorecard"
    assert calls[2][1]["path_params"] == {"matchId": "147931"}


def test_refresh_cooldown_survives_calls_and_failures(live_db):
    gate, calls = coordinator(error=APIError("rate_limit", "safe", retry_after=90))
    with pytest.raises(APIError, match="safe"):
        gate.refresh(live_db)
    assert gate.next_allowed == 190
    with pytest.raises(APIError) as e:
        gate.refresh(live_db)
    assert e.value.code == "cooldown"
    assert len(calls) == 2
    assert LiveMatchService(live_db).matches() == []


def test_busy_refresh_lock_does_not_send(live_db):
    gate, calls = coordinator()
    gate.lock.acquire()
    try:
        with pytest.raises(APIError) as e:
            gate.refresh(live_db)
        assert e.value.code == "cooldown" and not calls
    finally:
        gate.lock.release()


@pytest.mark.parametrize("mode", ["sample", "readonly", "schema1"])
def test_refresh_preflight_before_loading_api(database, mode):
    if mode == "readonly":
        database.settings = replace(
            database.settings, data_mode="live", access_mode="public_readonly"
        )
    elif mode == "schema1":
        with database.transaction(write=True) as c:
            c.exec_driver_sql("UPDATE dataset_state SET mode='live'")
            c.exec_driver_sql("PRAGMA user_version=1")
        database.settings = replace(database.settings, data_mode="live")

    def forbidden():
        raise AssertionError("No API setup before preflight")

    gate = RefreshCoordinator(settings_loader=forbidden)
    with pytest.raises(APIError):
        gate.refresh(database)


def test_unverified_match_refuses_scorecard_without_spending_quota(live_db):
    gate, calls = coordinator()
    with pytest.raises(APIError):
        gate.refresh(live_db, 999)
    assert calls == []


def test_empty_provider_list_is_successful_without_fabricating_matches(live_db):
    gate, _ = coordinator(empty=True)
    result = gate.refresh(live_db)
    assert result["status"] == "committed" and result["match_count"] == 0
    assert LiveMatchService(live_db).matches() == []


def test_sample_page_defaults_to_all_then_filters_without_network(
    settings, monkeypatch
):
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("Unexpected HTTP")
    ) as network:
        at = page(settings, monkeypatch)
        assert not at.exception
        assert at.selectbox(key="live_status").value == "All saved matches"
        assert at.dataframe
        at.selectbox(key="live_status").select("Ongoing in saved data").run()
        assert any("No matches match" in x.value for x in at.info)
        at.selectbox(key="live_status").select("All saved matches").run()
        assert not at.exception and at.dataframe
        assert at.button(key="refresh_live_list").disabled
        assert at.button(key="refresh_live_scorecard").disabled
        at.selectbox(key="selected_live_match").select(1).run()
        assert not at.exception and not network.called


def test_live_page_refresh_button_fetches_once_not_on_filter_rerun(
    live_db, monkeypatch
):
    gate, calls = coordinator()
    monkeypatch.setattr("ui.live_matches.refresh_coordinator", lambda: gate)
    at = page(live_db.settings, monkeypatch)
    assert calls == [] and not at.exception
    at.button(key="refresh_live_list").click().run()
    assert not at.exception and at.success
    assert len(calls) == 2
    at.selectbox(key="live_status").select("All saved matches").run()
    assert len(calls) == 2 and not at.exception


def test_refresh_error_is_redacted_and_saved_ui_remains(live_db, monkeypatch):
    gate, _ = coordinator(error=APIError("authentication", "secret-must-not-render"))
    monkeypatch.setattr("ui.live_matches.refresh_coordinator", lambda: gate)
    at = page(live_db.settings, monkeypatch)
    at.button(key="refresh_live_list").click().run()
    assert not at.exception and at.warning
    assert "secret-must-not-render" not in str([x.value for x in at.warning])


def test_readonly_page_and_missing_database(settings, monkeypatch, tmp_path):
    at = page(replace(settings, access_mode="public_readonly"), monkeypatch)
    assert at.button(key="refresh_live_list").disabled
    target = tmp_path / "absent.db"
    at = page(replace(settings, database_path=target), monkeypatch)
    assert at.warning and not at.exception and not target.exists()
