"""Safe fixture ingestion and explicit raw HTTP smoke-check commands."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

from sqlalchemy import text

from api.adapter import decode_snapshot
from api.client import APIError, CricbuzzClient
from api.configuration import load_api_settings
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer
from api.scorecard import CricbuzzV2ScorecardNormalizer
from config import ConfigurationError, load_settings
from services.ingestion import IngestionService
from services.matches import MatchService
from services.player_stats import PlayerStatsService
from utils.db_connection import Database, DatabaseError, schema_version


def _pairs(values):
    """Parse explicit name=value CLI arguments into a parameter mapping."""
    result = {}
    for item in values:
        if "=" not in item:
            raise ValueError("Parameters must use name=value.")
        key, value = item.split("=", 1)
        if not key or key in result:
            raise ValueError("Parameters need distinct nonempty names.")
        result[key] = value
    return result


def sync_live(
    database_path: Path | None,
    match_id: str | None = None,
    *,
    operation="live_matches",
    series_id=None,
    scope=None,
) -> dict:
    """Validate an existing live target before spending any provider request."""
    settings = live_settings(database_path)
    database = Database(settings)
    client = None
    try:
        with database.transaction() as connection:
            if schema_version(connection) != 2:
                raise DatabaseError(
                    "Live sync requires schema 2; migrate explicitly first."
                )
        normalizer = CricbuzzV2MatchListNormalizer()
        path_params = None
        if operation == "series_matches":
            from api.series import CricbuzzV2SeriesNormalizer

            normalizer = CricbuzzV2SeriesNormalizer(series_id, scope)
            path_params = {"seriesId": str(series_id)}
        if match_id is not None:
            with database.transaction() as connection:
                teams = connection.execute(
                    text(
                        "SELECT t.name,t.external_id FROM match_teams mt "
                        "JOIN matches m ON m.match_id=mt.match_id "
                        "JOIN teams t ON t.team_id=mt.team_id "
                        "JOIN sources s ON s.source_id=m.source_id "
                        "WHERE m.external_id=:mid AND s.name=:source"
                    ),
                    {
                        "mid": match_id,
                        "source": "cricketapilive-cricbuzz-cricket/v2/provider",
                    },
                ).all()
            normalizer = CricbuzzV2ScorecardNormalizer(match_id, dict(teams))
            operation, path_params = "match_scorecard", {"matchId": match_id}
        api_settings = load_api_settings()
        client = CricbuzzClient(
            api_settings.contract, api_settings.api_key, policy=api_settings.policy
        )
        observed = SyncNormalizer(normalizer)
        result = MatchService(database, client, observed).refresh(
            operation, path_params=path_params
        )
        return {
            "origin": "provider",
            "database_imported": True,
            "quota": observed.quota,
            "fetched_at": observed.fetched_at,
            **result.__dict__,
        }
    finally:
        if client is not None:
            client.close()
        database.close()


def sync_player(database_path: Path | None, player_id: str):
    """Check target and identifier before loading credentials or making requests."""
    from api.players import CricbuzzV2PlayerNormalizer

    CricbuzzV2PlayerNormalizer(player_id)
    database = Database(live_settings(database_path))
    client = None
    try:
        with database.transaction() as connection:
            if schema_version(connection) != 2:
                raise DatabaseError("Player sync requires schema 2.")
        settings = load_api_settings()
        client = CricbuzzClient(
            settings.contract, settings.api_key, policy=settings.policy
        )
        return PlayerStatsService(database, client).refresh_player(player_id)
    finally:
        if client is not None:
            client.close()
        database.close()


class SyncNormalizer:
    """Retain only allowlisted request evidence alongside the verified delegate."""

    def __init__(self, delegate):
        """Share delegate provenance without retaining credentials or raw headers."""
        self.delegate = delegate
        self.provider, self.version = delegate.provider, delegate.version
        self.quota = {}
        self.fetched_at = None

    def normalize(self, response):
        """Normalize the response and remember its safe quota/fetch metadata."""
        snapshot = self.delegate.normalize(response)
        self.quota = response.quota
        self.fetched_at = response.fetched_at
        return snapshot


def live_settings(database_path):
    """Select an explicit SQLite path or the privately configured live backend."""
    settings = load_settings()
    if database_path is not None:
        return replace(
            settings,
            data_mode="live",
            database_path=database_path.expanduser().resolve(),
            database_url=None,
            read_database_url=None,
        )
    if settings.data_mode != "live":
        raise DatabaseError("Configured provider imports require DATA_MODE=live.")
    return settings


def target_arguments(parser):
    """Require an explicit file target or an explicit configured-backend selection."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--database", type=Path)
    group.add_argument("--configured", action="store_true")


def main():
    """Never start network requests or write data without an explicit command."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check-config")
    sync = commands.add_parser("sync-live")
    target_arguments(sync)
    scorecard = commands.add_parser("sync-scorecard")
    scorecard.add_argument("match_id")
    target_arguments(scorecard)
    player = commands.add_parser("sync-player")
    player.add_argument("player_id")
    target_arguments(player)
    recent = commands.add_parser("sync-recent")
    target_arguments(recent)
    series = commands.add_parser("sync-series")
    series.add_argument("series_id")
    series.add_argument(
        "--scope",
        choices=["International", "Domestic", "League", "Women"],
        required=True,
    )
    target_arguments(series)
    fixture = commands.add_parser("import-fixture")
    fixture.add_argument("fixture", type=Path)
    fixture.add_argument("--database", type=Path, required=True)
    request = commands.add_parser("request")
    request.add_argument("operation")
    request.add_argument("--path-param", action="append", default=[])
    request.add_argument("--query", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.command == "sync-live":
            print(json.dumps(sync_live(args.database), indent=2))
        elif args.command == "sync-recent":
            print(
                json.dumps(
                    sync_live(args.database, operation="recent_matches"), indent=2
                )
            )
        elif args.command == "sync-series":
            print(
                json.dumps(
                    sync_live(
                        args.database,
                        operation="series_matches",
                        series_id=args.series_id,
                        scope=args.scope,
                    ),
                    indent=2,
                )
            )
        elif args.command == "sync-scorecard":
            print(json.dumps(sync_live(args.database, args.match_id), indent=2))
        elif args.command == "sync-player":
            print(json.dumps(sync_player(args.database, args.player_id), indent=2))
        elif args.command == "import-fixture":
            if args.fixture.stat().st_size > 2_000_000:
                raise ValueError("Fixture is too large.")
            snapshot = decode_snapshot(
                json.loads(args.fixture.read_text()), origin="synthetic"
            )
            settings = replace(
                load_settings(), database_path=args.database.expanduser().resolve()
            )
            database = Database(settings)
            try:
                result = IngestionService(database).ingest(snapshot)
                print(json.dumps({"origin": "synthetic", **result.__dict__}, indent=2))
            finally:
                database.close()
        else:
            settings = load_api_settings()
            if args.command == "check-config":
                print(
                    json.dumps(
                        {
                            "provider": settings.contract.provider,
                            "version": settings.contract.version,
                            "operations": sorted(settings.contract.endpoints),
                            "credential_configured": True,
                            "live_verified": False,
                        },
                        indent=2,
                    )
                )
            else:
                client = CricbuzzClient(
                    settings.contract, settings.api_key, policy=settings.policy
                )
                try:
                    response = client.get(
                        args.operation,
                        path_params=_pairs(args.path_param),
                        query=_pairs(args.query),
                    )
                    print(
                        json.dumps(
                            {
                                "provider": response.provider,
                                "version": response.version,
                                "operation": response.operation,
                                "fetched_at": response.fetched_at,
                                "is_mock": response.is_mock,
                                "quota": response.quota,
                                "database_imported": False,
                            },
                            indent=2,
                        )
                    )
                finally:
                    client.close()
    except APIError as error:
        parser.exit(1, f"API operation unavailable ({error.code}): {error}\n")
    except (ConfigurationError, DatabaseError, ValueError, OSError, TypeError):
        parser.exit(
            1, "Invalid API configuration, fixture, database or command parameters.\n"
        )


if __name__ == "__main__":
    main()
