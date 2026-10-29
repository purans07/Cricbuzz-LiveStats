"""Internal normalized-schema validation; fixtures are explicitly synthetic."""

import json
from pathlib import Path

import pytest

from api.adapter import decode_snapshot
from api.client import APIError
from api.configuration import load_api_settings

FIXTURE = Path(__file__).parent / "fixtures/normalized_match.json"


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text())


def test_decode_has_stable_digest_and_immutable_records(payload):
    first = decode_snapshot(payload)
    assert first.origin == "synthetic"
    assert len(first.groups) == 18
    assert first.digest == decode_snapshot(payload).digest
    first.groups[0]["rows"].clear()
    assert first.groups[0]["rows"]
    payload["tables"][0]["rows"].clear()
    assert first.groups[0]["rows"]


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_table",
        "local_id",
        "protected_column",
        "unknown_meta",
        "bad_timestamp",
        "duplicate_group",
        "wrong_shape",
    ],
)
def test_reject_malformed_normalized_records(payload, mutation):
    if mutation == "unknown_table":
        payload["tables"][0]["table"] = "sqlite_master"
    elif mutation == "local_id":
        payload["tables"][3]["rows"][0]["country_id"] = 123
    elif mutation == "protected_column":
        payload["tables"][3]["rows"][0]["source_id"] = 123
    elif mutation == "unknown_meta":
        payload["metadata"]["secret"] = "do-not-echo"
    elif mutation == "bad_timestamp":
        payload["metadata"]["fetched_at"] = "not-a-date"
    elif mutation == "duplicate_group":
        payload["tables"].append(payload["tables"][0])
    else:
        payload["tables"][0]["rows"] = {}
    with pytest.raises(APIError) as caught:
        decode_snapshot(payload)
    assert "do-not-echo" not in str(caught.value)


def test_unknown_origin_rejected(payload):
    with pytest.raises(APIError):
        decode_snapshot(payload, origin="gateway_mock")


def test_missing_provider_configuration_is_actionable():
    with pytest.raises(APIError, match="Select a provider"):
        load_api_settings(environ={})


def test_unverified_manifest_never_loads_credential(tmp_path):
    path = tmp_path / "provider.json"
    path.write_text('{"verified": false}')
    with pytest.raises(APIError) as caught:
        load_api_settings(
            environ={
                "CRICBUZZ_CONTRACT_FILE": str(path),
                "CRICBUZZ_API_KEY": "private-test-value",
            }
        )
    assert "private-test-value" not in str(caught.value)


def test_valid_explicit_manifest_and_secret_repr(tmp_path):
    path = tmp_path / "provider.json"
    path.write_text(
        json.dumps(
            {
                "provider": "test",
                "version": "test-v1",
                "verified": True,
                "base_url": "https://fixture.example",
                "auth_header": "X-Test-Key",
                "endpoints": {"live_matches": {"path": "/live"}},
            }
        )
    )
    settings = load_api_settings(
        environ={
            "CRICBUZZ_CONTRACT_FILE": str(path),
            "CRICBUZZ_API_KEY": "private-test-value",
        }
    )
    assert settings.contract.provider == "test"
    assert "private-test-value" not in repr(settings)
