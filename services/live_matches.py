"""Saved match/scorecard reads and explicit, rate-limited dashboard refreshes."""

from threading import Lock
from time import monotonic

from sqlalchemy import text

from api.client import APIError, CricbuzzClient
from api.configuration import load_api_settings
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer
from api.scorecard import CricbuzzV2ScorecardNormalizer
from services.matches import MatchService
from utils.db_connection import schema_version

PROVIDER_SOURCE = "cricketapilive-cricbuzz-cricket/v2/provider"
MATCH_SQL = """
SELECT m.match_id,m.external_id,m.description,m.status,m.status_text,m.starts_at,
       f.code AS format, v.name AS venue,v.city,s.name AS source,
       b.fetched_at,b.completeness,a.name AS team1,z.name AS team2
FROM matches m JOIN formats f ON f.format_id=m.format_id
LEFT JOIN venues v ON v.venue_id=m.venue_id
LEFT JOIN sources s ON s.source_id=m.source_id
LEFT JOIN import_batches b ON b.batch_id=m.last_batch_id
LEFT JOIN match_teams x ON x.match_id=m.match_id AND x.slot=1
LEFT JOIN teams a ON a.team_id=x.team_id
LEFT JOIN match_teams y ON y.match_id=m.match_id AND y.slot=2
LEFT JOIN teams z ON z.team_id=y.team_id
ORDER BY m.starts_at DESC,m.match_id DESC
"""


class LiveMatchService:
    """Read tables in one transaction per page read; never infer absent statistics."""

    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def matches(self):
        """Read visible saved matches with their status and provenance."""
        with self.database.transaction() as c:
            return [dict(r) for r in c.execute(text(MATCH_SQL)).mappings()]

    def scorecard(self, match_id):
        """Read the selected saved match and its per-innings performance records."""
        if type(match_id) is not int or match_id <= 0:
            raise ValueError("Select a valid stored match.")
        with self.database.transaction() as c:
            innings = [
                dict(r)
                for r in c.execute(
                    text("""
                SELECT i.*,t.name AS batting_team,b.fetched_at,b.completeness
                FROM innings i JOIN teams t ON t.team_id=i.batting_team_id
                LEFT JOIN import_batches b ON b.batch_id=i.last_batch_id
                WHERE i.match_id=:mid ORDER BY i.innings_number
            """),
                    {"mid": match_id},
                ).mappings()
            ]
            for inning in innings:
                for kind, view, fields, order in (
                    (
                        "batting",
                        "v_active_batting",
                        "s.batting_position,s.runs,s.balls_faced,s.fours,s.sixes,s.dismissal_text,s.is_dismissed",
                        "s.batting_position IS NULL,s.batting_position,s.player_id",
                    ),
                    (
                        "bowling",
                        "v_active_bowling",
                        "s.legal_balls,s.maidens,s.runs_conceded,s.wickets",
                        "s.player_id",
                    ),
                ):
                    # SQL identifiers and fields are fixed tuples, never UI input.
                    query = f"""SELECT p.full_name AS player,{fields},s.ownership,
                        b.fetched_at AS imported_at FROM {view} s
                        JOIN players p ON p.player_id=s.player_id
                        LEFT JOIN import_batches b ON b.batch_id=s.last_batch_id
                        WHERE s.innings_id=:iid ORDER BY {order}"""
                    inning[kind] = [
                        dict(r)
                        for r in c.execute(
                            text(query), {"iid": inning["innings_id"]}
                        ).mappings()
                    ]
            return innings


class _ObservedNormalizer:
    """Keep only safe snapshot metadata for the refresh confirmation."""

    def __init__(self, delegate):
        """Retain validated dependencies for this component without performing its operations."""
        self.delegate = delegate
        self.provider, self.version = delegate.provider, delegate.version
        self.metadata = {}

    def normalize(self, response):
        """Validate provider provenance and map supported response fields into a snapshot."""
        snapshot = self.delegate.normalize(response)
        self.metadata = {
            "fetched_at": snapshot.fetched_at,
            "match_count": sum(
                len(g["rows"]) for g in snapshot.groups if g["table"] == "matches"
            ),
        }
        return snapshot


class RefreshCoordinator:
    """Process-wide serialized requests and cooldown; no credential cache."""

    def __init__(
        self,
        *,
        clock=monotonic,
        settings_loader=load_api_settings,
        client_factory=CricbuzzClient,
    ):
        """Retain validated dependencies for this component without performing its operations."""
        self.clock, self.settings_loader, self.client_factory = (
            clock,
            settings_loader,
            client_factory,
        )
        self.lock = Lock()
        self.next_allowed = 0.0

    def refresh(self, database, match_id=None):
        """Fetch supported provider data explicitly and import it under refresh safeguards."""
        settings = database.settings
        if settings.data_mode != "live" or settings.access_mode != "local":
            raise APIError("configuration", "Refresh requires a writable live dataset.")
        with database.transaction() as c:
            if schema_version(c) != 2:
                raise APIError(
                    "configuration", "Refresh requires the current database schema."
                )
            delegate = CricbuzzV2MatchListNormalizer()
            operation, params = "live_matches", None
            if match_id is not None:
                if type(match_id) is not int or match_id <= 0:
                    raise APIError("input", "Select a valid provider match.")
                match = c.execute(
                    text("""SELECT m.external_id,s.name FROM matches m
                    JOIN sources s ON s.source_id=m.source_id WHERE m.match_id=:mid"""),
                    {"mid": match_id},
                ).first()
                if match is None or match.name != PROVIDER_SOURCE:
                    raise APIError(
                        "input", "This match has no verified provider identity."
                    )
                teams = c.execute(
                    text("""SELECT t.name,t.external_id FROM match_teams mt
                    JOIN teams t ON t.team_id=mt.team_id JOIN sources s ON s.source_id=t.source_id
                    WHERE mt.match_id=:mid AND s.name=:source"""),
                    {"mid": match_id, "source": PROVIDER_SOURCE},
                ).all()
                try:
                    delegate = CricbuzzV2ScorecardNormalizer(
                        match.external_id, dict(teams)
                    )
                except ValueError:
                    raise APIError(
                        "input", "Verified match participants are unavailable."
                    ) from None
                operation, params = "match_scorecard", {"matchId": match.external_id}
        if not self.lock.acquire(blocking=False):
            raise APIError("cooldown", "A provider refresh is already running.")
        client = None
        try:
            if self.clock() < self.next_allowed:
                raise APIError(
                    "cooldown",
                    "Wait before refreshing again.",
                    self.next_allowed - self.clock(),
                )
            api = self.settings_loader()
            if (api.contract.provider, api.contract.version) != (
                delegate.provider,
                delegate.version,
            ):
                raise APIError(
                    "configuration",
                    "The selected API contract does not match this page.",
                )
            self.next_allowed = self.clock() + max(30, api.policy.min_interval)
            client = self.client_factory(api.contract, api.api_key, policy=api.policy)
            observed = _ObservedNormalizer(delegate)
            result = MatchService(database, client, observed).refresh(
                operation, path_params=params
            )
            return {"status": result.status, **observed.metadata}
        except APIError as error:
            if error.retry_after is not None:
                self.next_allowed = max(
                    self.next_allowed, self.clock() + error.retry_after
                )
            raise
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                self.lock.release()
