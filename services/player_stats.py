"""Stored career snapshots and reuse of verified provider refresh orchestration."""

from time import sleep

from sqlalchemy import text

from api.client import APIError
from api.players import CricbuzzV2PlayerNormalizer
from services.ingestion import IngestionService
from services.matches import MatchService
from utils.db_connection import schema_version


class PlayerStatsService(MatchService):
    """Do not confuse dataset aggregates with provider career statistics."""

    def refresh_player(self, player_id, *, pause=sleep):
        """Fetch all three scopes before one write; a failed request imports nothing."""
        normalizer = CricbuzzV2PlayerNormalizer(player_id)
        if self.client is None or (
            self.client.contract.provider != normalizer.provider
            or self.client.contract.version != normalizer.version
        ):
            raise APIError("configuration", "A matching player provider is required.")
        with self.database.transaction() as connection:
            if (
                self.database.settings.data_mode != "live"
                or self.database.settings.access_mode != "local"
                or schema_version(connection) != 2
            ):
                raise APIError(
                    "configuration",
                    "Player refresh requires a writable live schema 2 database.",
                )
        delay = self.client.policy.min_interval
        if delay > 60:
            raise APIError(
                "cooldown", "Request interval is too long for a player refresh."
            )
        responses = []
        for operation in ("player_profile", "player_batting", "player_bowling"):
            if responses:
                pause(delay)
            responses.append(
                self.client.get(operation, path_params={"playerId": str(player_id)})
            )
        snapshot = normalizer.normalize_bundle(*responses)
        result = IngestionService(self.database).ingest(snapshot)
        return {
            "origin": "provider",
            **result.__dict__,
            "subrequests": [
                {
                    "operation": r.operation,
                    "fetched_at": r.fetched_at,
                    "is_mock": r.is_mock,
                    "quota": r.quota,
                }
                for r in responses
            ],
        }

    def profile(self, player_id):
        """Read a stored local player ID and role without a network request."""
        with self.database.transaction() as connection:
            row = (
                connection.execute(
                    text(
                        "SELECT p.*,r.name AS role FROM v_active_players p "
                        "LEFT JOIN playing_roles r ON r.role_id=p.role_id WHERE p.player_id=:id"
                    ),
                    {"id": player_id},
                )
                .mappings()
                .first()
            )
            return dict(row) if row else None

    def latest_career(self, format_code: str):
        """Return distinct-source latest career rows without inventing rankings."""
        with self.database.transaction() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT c.*,p.full_name,f.code AS format_code FROM v_latest_career c "
                        "JOIN players p ON p.player_id=c.player_id "
                        "JOIN formats f ON f.format_id=c.format_id "
                        "WHERE f.code=:format ORDER BY c.player_id,c.source_id"
                    ),
                    {"format": format_code},
                ).mappings()
            ]
