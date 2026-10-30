"""Publish validated cricket snapshots without exposing credentials or write controls."""

import json
from dataclasses import replace
from pathlib import Path

from api.adapter import decode_snapshot
from api.client import CricbuzzClient
from api.configuration import load_api_settings
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer
from config import PROJECT_ROOT, load_settings
from database.initialize import initialize_database
from services.ingestion import IngestionService
from services.overview import OverviewService
from utils.db_connection import Database

PUBLIC_DATA = PROJECT_ROOT / "data/public_provider"


def snapshot_payload(snapshot):
    """Serialize normalized sporting records only, without request headers or keys."""
    return {
        "metadata": {
            "schema_version": 1,
            "provider": snapshot.provider,
            "provider_version": snapshot.provider_version,
            "capability": snapshot.capability,
            "resource_key": snapshot.resource_key,
            "fetched_at": snapshot.fetched_at,
            "upstream_updated_at": snapshot.upstream_updated_at,
            "completeness": snapshot.completeness,
        },
        "tables": snapshot.groups,
    }


def prepare_public_provider(directory=PUBLIC_DATA, database_path=None):
    """Apply trusted bundled snapshots during startup, then return readonly settings."""
    settings = load_settings(
        environ={
            "DATA_MODE": "live",
            "APP_ACCESS_MODE": "local",
            "DATABASE_URL": "sqlite:///"
            + str(database_path or PROJECT_ROOT / "data/runtime/public-provider.db"),
        }
    )
    files = sorted(Path(directory).glob("*.json"))
    if not files:
        raise ValueError("No verified provider snapshots are bundled.")
    snapshots = [
        decode_snapshot(json.loads(p.read_text()), origin="provider") for p in files
    ]
    if not settings.database_path.exists():
        try:
            initialize_database(settings)
        except FileExistsError:
            pass
    database = Database(settings)
    try:
        # Service transactions enforce mode, schema, fingerprints and stale protection.
        for snapshot in snapshots:
            IngestionService(database).ingest(snapshot)
        OverviewService(database).read()
    finally:
        database.close()
    return replace(settings, access_mode="public_readonly")


def refresh_public_feed():
    """Make one scheduled live-list request; retain old file if validation fails."""
    api = load_api_settings()
    client = CricbuzzClient(api.contract, api.api_key, policy=api.policy)
    try:
        response = client.get("live_matches")
        snapshot = CricbuzzV2MatchListNormalizer().normalize(response)
        payload = snapshot_payload(snapshot)
        # Exercise relational import in an isolated target before publication.
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            trial = Path(folder)
            (trial / "live.json").write_text(json.dumps(payload))
            prepare_public_provider(trial, trial / "validation.db")
        PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
        target = PUBLIC_DATA / "90-latest-matches.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n")
        temporary.replace(target)
        print("Verified live match snapshot updated; one provider request used.")
    finally:
        client.close()


if __name__ == "__main__":
    refresh_public_feed()
