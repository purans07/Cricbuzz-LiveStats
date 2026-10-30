"""Publish validated cricket snapshots without exposing credentials or write controls."""

import json
import shutil
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from api.adapter import decode_snapshot
from api.client import APIError, CricbuzzClient
from api.configuration import load_api_settings
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer
from api.scorecard import CricbuzzV2ScorecardNormalizer
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
    snapshots.sort(key=lambda snapshot: snapshot.fetched_at)
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


def scorecard_candidates(directory, limit=2):
    """Select at most two current or missing completed ordinary scorecards."""
    if type(limit) is not int or not 0 <= limit <= 2:
        raise ValueError("Scorecard request budget must be between zero and two.")
    snapshots = sorted(
        (
            decode_snapshot(json.loads(p.read_text()), origin="provider")
            for p in Path(directory).glob("*.json")
        ),
        key=lambda snapshot: snapshot.fetched_at,
    )
    teams, matches, participants, detailed = {}, {}, {}, set()
    latest_live_ids = set()
    for snapshot in snapshots:
        if snapshot.capability == "live_matches":
            latest_live_ids = {
                row["external_id"]
                for group in snapshot.groups
                if group["table"] == "matches"
                for row in group["rows"]
            }
        for group in snapshot.groups:
            for row in group["rows"]:
                if group["table"] == "teams":
                    teams[row["external_id"]] = row["name"]
                elif group["table"] == "matches":
                    matches[row["external_id"]] = row
                elif group["table"] == "match_teams":
                    participants.setdefault(row["match_id"]["external_id"], {})[
                        row["team_id"]["external_id"]
                    ] = row["slot"]
        if snapshot.capability == "match_scorecard":
            has_batting = any(
                g["table"] == "batting_performances" and g["rows"]
                for g in snapshot.groups
            )
            has_bowling = any(
                g["table"] == "bowling_performances" and g["rows"]
                for g in snapshot.groups
            )
            if has_batting and has_bowling:
                detailed.add(snapshot.resource_key)
    selected = []
    for mid, match in sorted(
        matches.items(),
        key=lambda item: (
            item[1].get("status") == "live",
            item[1].get("starts_at", ""),
            item[0],
        ),
        reverse=True,
    ):
        if match.get("status") not in {"live", "completed"}:
            continue
        if match.get("status") == "live" and mid not in latest_live_ids:
            continue
        if match.get("status") == "completed" and mid in detailed:
            continue
        code = match["format_id"]["code"]
        if "HUNDRED" in code or "HUN" == code:
            continue
        mapping = {teams[tid]: tid for tid in participants.get(mid, {}) if tid in teams}
        if len(mapping) == 2:
            selected.append((mid, mapping))
        if len(selected) == limit:
            break
    return selected if limit else []


def publish_snapshot(snapshot, filename, directory=PUBLIC_DATA):
    """Validate against the full feed before atomically replacing a public file."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = snapshot_payload(snapshot)
    with tempfile.TemporaryDirectory() as folder:
        trial = Path(folder)
        for existing in directory.glob("*.json"):
            shutil.copy2(existing, trial / existing.name)
        (trial / filename).write_text(json.dumps(payload))
        prepare_public_provider(trial, trial / "validation.db")
    target = directory / filename
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    temporary.replace(target)


def refresh_public_feed():
    """Use one list request plus at most two scorecards; retain failed details."""
    api = load_api_settings()
    client = CricbuzzClient(api.contract, api.api_key, policy=api.policy)
    try:
        response = client.get("live_matches")
        publish_snapshot(
            CricbuzzV2MatchListNormalizer().normalize(response),
            "90-latest-matches.json",
        )
        print("Verified match list published; one request used.")
        for mid, teams in scorecard_candidates(PUBLIC_DATA):
            time.sleep(api.policy.min_interval)
            try:
                response = client.get("match_scorecard", path_params={"matchId": mid})
                snapshot = CricbuzzV2ScorecardNormalizer(mid, teams).normalize(response)
                publish_snapshot(snapshot, f"95-scorecard-{mid}.json")
                print(f"Verified scorecard {mid} published.")
            except (APIError, ValueError) as error:
                code = error.code if isinstance(error, APIError) else "validation"
                print(f"Scorecard {mid} retained: {code}.")
                if code in {"authentication", "rate_limit"}:
                    break
    finally:
        client.close()


if __name__ == "__main__":
    refresh_public_feed()
