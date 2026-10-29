"""Atomic imports and freshness/ownership rules use synthetic snapshots only."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from api.adapter import decode_snapshot
from api.client import APIError
from config import load_settings
from database.initialize import initialize_database
from services.ingestion import IngestionService
from services.matches import MatchService
from services.player_stats import PlayerStatsService
from utils.db_connection import Database

FIXTURE = Path(__file__).parent / "fixtures/normalized_match.json"


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def api_database(tmp_path):
    settings = replace(
        load_settings(environ={}), database_path=tmp_path / "api-fixture.db"
    )
    initialize_database(settings)
    database = Database(settings)
    yield database
    database.close()


def rows(payload, table):
    return next(group["rows"] for group in payload["tables"] if group["table"] == table)


def later(payload):
    payload["metadata"]["fetched_at"] = "2026-10-21T11:00:00Z"
    payload["metadata"]["upstream_updated_at"] = "2026-10-21T10:59:00Z"
    return payload


def status(database):
    with database.transaction() as c:
        return c.exec_driver_sql("SELECT revision FROM dataset_state").scalar_one()


def test_import_graph_and_source_provenance(api_database, payload):
    result = IngestionService(api_database).ingest(decode_snapshot(payload))
    assert result.status == "committed"
    with api_database.transaction() as c:
        assert c.exec_driver_sql("SELECT COUNT(*) FROM matches").scalar_one() == 1
        assert c.exec_driver_sql("SELECT COUNT(*) FROM innings").scalar_one() == 2
        assert (
            c.exec_driver_sql("SELECT COUNT(*) FROM v_latest_career").scalar_one() == 2
        )
        assert c.exec_driver_sql("SELECT kind FROM sources").scalar_one() == "sample"
        assert c.exec_driver_sql("PRAGMA foreign_key_check").fetchall() == []
        assert (
            c.exec_driver_sql("SELECT status FROM import_batches").scalar_one()
            == "committed"
        )
    assert status(api_database) == 1


def test_exact_duplicate_changes_nothing(api_database, payload):
    service = IngestionService(api_database)
    snapshot = decode_snapshot(payload)
    first = service.ingest(snapshot)
    second = service.ingest(snapshot)
    assert second.status == "duplicate" and second.batch_id == first.batch_id
    assert status(api_database) == 1
    with api_database.transaction() as c:
        assert (
            c.exec_driver_sql("SELECT COUNT(*) FROM import_batches").scalar_one() == 1
        )


def test_new_snapshot_updates_existing_logical_rows(api_database, payload):
    service = IngestionService(api_database)
    service.ingest(decode_snapshot(payload))
    later(payload)
    rows(payload, "batting_performances")[0]["runs"] = 70
    result = service.ingest(decode_snapshot(payload))
    assert result.status == "committed"
    with api_database.transaction() as c:
        assert c.exec_driver_sql("SELECT COUNT(*) FROM matches").scalar_one() == 1
        assert (
            c.exec_driver_sql("SELECT COUNT(*) FROM batting_performances").scalar_one()
            == 2
        )
        assert (
            c.exec_driver_sql(
                "SELECT runs FROM batting_performances WHERE team_id=1"
            ).scalar_one()
            == 70
        )
    assert status(api_database) == 2


def test_stale_snapshot_changes_nothing(api_database, payload):
    service = IngestionService(api_database)
    original = decode_snapshot(payload)
    service.ingest(decode_snapshot(later(payload)))
    result = service.ingest(original)
    assert result.status == "stale" and status(api_database) == 1


def test_partial_unknown_values_do_not_erase_known_values(api_database, payload):
    service = IngestionService(api_database)
    service.ingest(decode_snapshot(payload))
    later(payload)
    rows(payload, "players")[0]["full_name"] = None
    rows(payload, "batting_performances")[0]["runs"] = None
    rows(payload, "players")[1].pop("bowling_style")
    service.ingest(decode_snapshot(payload))
    with api_database.transaction() as c:
        assert (
            c.exec_driver_sql(
                "SELECT runs FROM batting_performances WHERE team_id=1"
            ).scalar_one()
            == 60
        )
        assert (
            c.exec_driver_sql(
                "SELECT full_name FROM players WHERE external_id='player-alpha'"
            ).scalar_one()
            == "Synthetic Alpha Player"
        )


@pytest.mark.parametrize(
    "ownership,deleted", [("manual", 0), ("override", 0), ("override", 1)]
)
def test_manual_and_override_records_are_preserved(
    api_database, payload, ownership, deleted
):
    service = IngestionService(api_database)
    service.ingest(decode_snapshot(payload))
    with api_database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE players SET full_name=?,ownership=?,is_deleted=? WHERE player_id=1",
            ("Operator correction", ownership, deleted),
        )
        c.exec_driver_sql(
            "UPDATE batting_performances SET runs=99,ownership=?,is_deleted=? WHERE player_id=1",
            (ownership, deleted),
        )
    later(payload)
    rows(payload, "players")[0]["full_name"] = "Provider change"
    rows(payload, "batting_performances")[0]["runs"] = 100
    service.ingest(decode_snapshot(payload))
    with api_database.transaction() as c:
        assert (
            c.exec_driver_sql(
                "SELECT full_name FROM players WHERE player_id=1"
            ).scalar_one()
            == "Operator correction"
        )
        assert (
            c.exec_driver_sql(
                "SELECT runs FROM batting_performances WHERE player_id=1"
            ).scalar_one()
            == 99
        )
        if deleted:
            assert (
                c.exec_driver_sql(
                    "SELECT COUNT(*) FROM v_active_batting WHERE player_id=1"
                ).scalar_one()
                == 0
            )


@pytest.mark.parametrize(
    "defect",
    [
        "wrong_team",
        "missing_player",
        "invalid_runs",
        "one_team",
        "reference_kind",
        "overlap",
    ],
)
def test_invalid_snapshot_rolls_back_whole_unit(api_database, payload, defect):
    if defect == "wrong_team":
        rows(payload, "batting_performances")[0]["team_id"]["external_id"] = "team-beta"
    elif defect == "missing_player":
        rows(payload, "batting_performances")[0]["player_id"]["external_id"] = (
            "not-present"
        )
    elif defect == "invalid_runs":
        rows(payload, "batting_performances")[0]["runs"] = -1
    elif defect == "one_team":
        rows(payload, "match_teams").pop()
    elif defect == "reference_kind":
        rows(payload, "batting_performances")[0]["team_id"] = {
            "table": "players",
            "external_id": "player-alpha",
        }
    else:
        membership = dict(rows(payload, "player_team_memberships")[0])
        membership["valid_from"] = "2026-10-22"
        rows(payload, "player_team_memberships").append(membership)
    with pytest.raises(APIError, match="rolled back"):
        IngestionService(api_database).ingest(decode_snapshot(payload))
    with api_database.transaction() as c:
        assert c.exec_driver_sql("SELECT COUNT(*) FROM players").scalar_one() == 0
        assert c.exec_driver_sql("SELECT COUNT(*) FROM sources").scalar_one() == 0
    assert status(api_database) == 0


def test_fixture_never_ingested_into_live_database(api_database, payload, tmp_path):
    live_settings = replace(
        api_database.settings, data_mode="live", database_path=tmp_path / "live.db"
    )
    initialize_database(live_settings)
    live = Database(live_settings)
    try:
        with pytest.raises(APIError, match="origin"):
            IngestionService(live).ingest(decode_snapshot(payload))
        assert status(live) == 0
    finally:
        live.close()


def test_completed_match_result_is_applied_after_participants(api_database, payload):
    match = rows(payload, "matches")[0]
    match.update(
        status="completed",
        result_type="win",
        winner_team_id={"table": "teams", "external_id": "team-alpha"},
        margin_value=50,
        margin_unit="runs",
    )
    IngestionService(api_database).ingest(decode_snapshot(payload))
    with api_database.transaction() as c:
        assert c.exec_driver_sql(
            "SELECT result_type,winner_team_id FROM matches"
        ).fetchone() == ("win", 1)


def test_unconfigured_live_service_makes_no_claim_of_success(api_database):
    with pytest.raises(APIError, match="verified"):
        MatchService(api_database).refresh("live_matches")


def test_stored_service_reads_are_scoped_and_network_free(api_database, payload):
    IngestionService(api_database).ingest(decode_snapshot(payload))
    matches = MatchService(api_database).stored_matches()
    assert len(matches) == 1 and "synthetic" in matches[0]["source"]
    assert len(PlayerStatsService(api_database).latest_career("ODI")) == 2
    assert PlayerStatsService(api_database).latest_career("T20I") == []


def test_provider_fixture_cannot_write_public_mode(api_database, payload):
    public = Database(replace(api_database.settings, access_mode="public_readonly"))
    try:
        with pytest.raises(APIError, match="local"):
            IngestionService(public).ingest(decode_snapshot(payload))
        assert status(api_database) == 0
    finally:
        public.close()


def test_gateway_mock_stops_before_normalizer_or_import(api_database):
    from api.client import APIResponse, ProviderContract

    class Client:
        contract = ProviderContract(
            "test-provider", "v1", "https://fixture.example", "X-Test-Key", {}
        )

        def get(self, *args, **kwargs):
            return APIResponse(
                {},
                "test-provider",
                "v1",
                "live_matches",
                "2026-10-21T10:00:00Z",
                True,
                {},
            )

    class Normalizer:
        provider = "test-provider"
        version = "v1"

        def normalize(self, response):
            raise AssertionError("Mock must not reach normalization")

    with pytest.raises(APIError, match="mock"):
        MatchService(api_database, Client(), Normalizer()).refresh("live_matches")
    assert status(api_database) == 0


def test_mismatched_adapter_prevents_http_request(api_database):
    from api.client import ProviderContract

    class Client:
        contract = ProviderContract(
            "test-provider", "v1", "https://fixture.example", "X-Test-Key", {}
        )

        def get(self, *args, **kwargs):
            raise AssertionError("Mismatch must not make a request")

    class Normalizer:
        provider = "different-provider"
        version = "v2"

    with pytest.raises(APIError, match="versions"):
        MatchService(api_database, Client(), Normalizer()).refresh("live_matches")
