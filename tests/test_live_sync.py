"""The reusable sync command preflights its database before any HTTP request."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import api.cli as cli
from api.client import APIResponse, HTTPPolicy, ProviderContract
from config import load_settings
from database.initialize import initialize_database
from utils.db_connection import DatabaseError


def test_missing_target_does_not_load_api_or_create_database(tmp_path, monkeypatch):
    def forbidden():
        raise AssertionError("API must not load before database preflight")

    monkeypatch.setattr(cli, "load_api_settings", forbidden)
    path = tmp_path / "missing.db"
    with pytest.raises(DatabaseError):
        cli.sync_live(path)
    assert not path.exists()


def test_sample_target_refused_before_http(settings, monkeypatch):
    def forbidden():
        raise AssertionError("API must not load for sample target")

    monkeypatch.setattr(cli, "load_api_settings", forbidden)
    with pytest.raises(DatabaseError, match="mode"):
        cli.sync_live(settings.database_path)


def test_reusable_sync_imports_with_injected_transport_only(tmp_path, monkeypatch):
    settings = replace(
        load_settings(environ={}), data_mode="live", database_path=tmp_path / "live.db"
    )
    initialize_database(settings)
    contract = ProviderContract(
        "cricketapilive-cricbuzz-cricket",
        "v2",
        "https://fixture.example",
        "X-Test-Key",
        {},
    )
    api_settings = SimpleNamespace(
        contract=contract, api_key="test-placeholder", policy=HTTPPolicy()
    )
    monkeypatch.setattr(cli, "load_api_settings", lambda: api_settings)
    observed = []

    class Client:
        def __init__(self, *args, **kwargs):
            self.contract = contract

        def get(self, operation, **kwargs):
            observed.append(operation)
            data = json.loads(
                (
                    Path(__file__).parent
                    / "fixtures/cricbuzz_v2_live_user_capture.json"
                ).read_text()
            )
            return APIResponse(
                data,
                contract.provider,
                contract.version,
                operation,
                "2026-10-22T06:30:44Z",
                False,
                {},
            )

        def close(self):
            observed.append("closed")

    monkeypatch.setattr(cli, "CricbuzzClient", Client)
    result = cli.sync_live(settings.database_path)
    assert result["database_imported"] and result["status"] == "committed"
    assert observed == ["live_matches", "closed"]
