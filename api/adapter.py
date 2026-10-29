"""Strict internal normalized snapshot contract, independent of vendor JSON.

This is not a parser for an unselected provider. Synthetic fixtures exercise
normalization and persistence until a real provider adapter can be verified.
"""

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field

from api.client import APIError
from utils.dates import normalize_timestamp

TABLE_ORDER = (
    "countries",
    "formats",
    "playing_roles",
    "teams",
    "venues",
    "series",
    "series_hosts",
    "series_formats",
    "players",
    "player_team_memberships",
    "matches",
    "match_teams",
    "match_players",
    "innings",
    "batting_performances",
    "bowling_performances",
    "fielding_performances",
    "career_stats_snapshots",
)
PROTECTED_COLUMNS = {
    "source_id",
    "last_batch_id",
    "batch_id",
    "version",
    "ownership",
    "is_deleted",
    "snapshot_id",
}
IDENTITY_COLUMNS = {
    "country_id",
    "format_id",
    "role_id",
    "team_id",
    "venue_id",
    "series_id",
    "player_id",
    "match_id",
    "innings_id",
    "membership_id",
    "batting_team_id",
    "bowling_team_id",
    "winner_team_id",
    "toss_winner_id",
}
REFERENCE_KEYS = {
    "countries": {"table", "name"},
    "formats": {"table", "code"},
    "playing_roles": {"table", "name"},
    **{
        name: {"table", "external_id"}
        for name in ("teams", "venues", "series", "players", "matches")
    },
    "innings": {"table", "match_external_id", "innings_number"},
}


@dataclass(frozen=True)
class Snapshot:
    """Owned copy of normalized records and durable duplicate-detection metadata."""

    provider: str
    provider_version: str
    capability: str
    resource_key: str
    fetched_at: str
    upstream_updated_at: str | None
    completeness: str
    origin: str
    _records_json: str = field(repr=False)
    digest: str

    @property
    def groups(self):
        """Return a fresh copy, so callers cannot mutate a fingerprinted snapshot."""
        return json.loads(self._records_json)

    @property
    def source_name(self):
        """Separate fixture/provider origins and versions in source identity."""
        return f"{self.provider}/{self.provider_version}/{self.origin}"


def decode_snapshot(payload: dict, *, origin: str = "synthetic") -> Snapshot:
    """Validate our normalized schema, not an arbitrary vendor response.

    Only trusted provider adapters may set origin='provider' after checking real
    response provenance. The fixture CLI always forces synthetic origin.
    """
    try:
        if set(payload) != {"metadata", "tables"}:
            raise ValueError
        meta = payload["metadata"]
        if set(meta) - {
            "schema_version",
            "provider",
            "provider_version",
            "capability",
            "resource_key",
            "fetched_at",
            "upstream_updated_at",
            "completeness",
        }:
            raise ValueError
        if meta["schema_version"] != 1 or origin not in {"synthetic", "provider"}:
            raise ValueError
        for key in ("provider", "provider_version", "capability", "resource_key"):
            if (
                not isinstance(meta[key], str)
                or not meta[key].strip()
                or len(meta[key]) > 200
            ):
                raise ValueError
        for key in ("provider", "provider_version", "capability"):
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", meta[key]):
                raise ValueError
        if not re.fullmatch(r"[A-Za-z0-9_.:/-]+", meta["resource_key"]):
            raise ValueError
        completeness = meta.get("completeness", "partial")
        if completeness not in {"partial", "complete", "unknown"}:
            raise ValueError
        fetched = normalize_timestamp(meta["fetched_at"])
        upstream = meta.get("upstream_updated_at")
        if upstream is not None:
            upstream = normalize_timestamp(upstream)
        groups, seen = [], set()
        if not isinstance(payload["tables"], list) or len(payload["tables"]) > len(
            TABLE_ORDER
        ):
            raise ValueError
        for group in payload["tables"]:
            if set(group) != {"table", "rows"}:
                raise ValueError
            table, rows = group["table"], group["rows"]
            if table not in TABLE_ORDER or table in seen or not isinstance(rows, list):
                raise ValueError
            if len(rows) > 5000:
                raise ValueError
            seen.add(table)
            for row in rows:
                if not isinstance(row, dict) or not row or PROTECTED_COLUMNS & set(row):
                    raise ValueError
                for key, value in row.items():
                    if key in IDENTITY_COLUMNS and value is not None:
                        if not isinstance(value, dict):
                            raise ValueError
                        target = value.get("table")
                        if (
                            target not in REFERENCE_KEYS
                            or set(value) != REFERENCE_KEYS[target]
                        ):
                            raise ValueError
                    elif isinstance(value, (dict, list)):
                        raise ValueError
            groups.append({"table": table, "rows": deepcopy(rows)})
        groups.sort(key=lambda g: TABLE_ORDER.index(g["table"]))
        canonical = {
            "metadata": {
                **meta,
                "fetched_at": fetched,
                "upstream_updated_at": upstream,
            },
            "tables": groups,
        }
        encoded = json.dumps(canonical, sort_keys=True, allow_nan=False).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        return Snapshot(
            meta["provider"],
            meta["provider_version"],
            meta["capability"],
            meta["resource_key"],
            fetched,
            upstream,
            completeness,
            origin,
            json.dumps(groups, sort_keys=True, allow_nan=False),
            digest,
        )
    except (TypeError, ValueError, KeyError, AttributeError):
        raise APIError(
            "normalization", "Normalized snapshot does not match the internal schema."
        ) from None
