"""Player profile and aligned career tables observed from cricketapilive v2."""

import math
import re

from api.adapter import decode_snapshot
from api.client import APIError
from api.cricbuzz_v2 import _id, _reference

FORMATS = {
    "Test": ("TEST", "TEST", "international"),
    "ODI": ("ODI", "ODI", "international"),
    # Retain the provider's T20 bucket without asserting official T20I eligibility.
    "T20": ("INTERNATIONAL_T20", "T20", "international"),
    "IPL": ("IPL", "T20", "domestic"),
}


def _integer(value):
    """Convert supported provider count cells while retaining unknown values as None."""
    if value in {None, "", "-", "--", "N/A"}:
        return None
    if type(value) not in {str, int} or not re.fullmatch(r"\d+", str(value)):
        raise ValueError("Invalid career count.")
    return int(value)


def _ratio(value, denominator):
    """Validate a finite nonnegative rate with a meaningful known denominator."""
    if denominator in {None, 0} or value in {None, "", "-", "--", "N/A"}:
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Invalid career ratio.")
    return result


def _table(payload):
    """Align supported career columns and reject duplicate labels or changed row widths."""
    headers = payload["headers"]
    if (
        not isinstance(headers, list)
        or not headers
        or headers[0] != "ROWHEADER"
        or len(set(headers)) != len(headers)
        or set(headers[1:]) - FORMATS.keys()
    ):
        raise ValueError("Unsupported career format columns.")
    result = {name: {} for name in headers[1:]}
    labels = set()
    for row in payload["values"]:
        values = row["values"]
        if not isinstance(values, list) or len(values) != len(headers):
            raise ValueError("Career table width changed.")
        label = values[0]
        if label in labels:
            raise ValueError("Duplicate statistic label.")
        labels.add(label)
        for name, value in zip(headers[1:], values[1:], strict=True):
            result[name][label] = value
    return result


class CricbuzzV2PlayerNormalizer:
    """Combine full-career batting and bowling in one atomic snapshot.

    Callers must fetch without seriesId, retain each response's fetch time and
    pass responses from the same player request. No series-filter parameter is
    exposed by the production contract.
    """

    provider = "cricketapilive-cricbuzz-cricket"
    version = "v2"

    def __init__(self, player_id):
        """Retain validated dependencies for this component without performing its operations."""
        self.player_id = _id(player_id)

    def normalize_bundle(self, profile, batting, bowling):
        """Validate aligned player responses and combine their career records atomically."""
        try:
            for response, operation in (
                (profile, "player_profile"),
                (batting, "player_batting"),
                (bowling, "player_bowling"),
            ):
                if (
                    response.provider != self.provider
                    or response.version != self.version
                    or response.operation != operation
                    or response.is_mock
                ):
                    raise ValueError("Response provenance mismatch.")
                if operation == "player_profile":
                    if _id(response.data["id"]) != self.player_id:
                        raise ValueError("Wrong player profile.")
                elif (
                    f"/profiles/{self.player_id}/"
                    not in response.data["appIndex"]["webURL"]
                ):
                    raise ValueError("Wrong player career table.")
            times = sorted(r.fetched_at for r in (profile, batting, bowling))
            from datetime import datetime

            if (
                datetime.fromisoformat(times[-1]) - datetime.fromisoformat(times[0])
            ).total_seconds() > 300:
                raise ValueError("Career subrequests are too far apart.")
            p = profile.data
            name = p.get("fullName") or p["name"]
            if not isinstance(name, str) or not name.strip():
                raise ValueError
            player = {"external_id": self.player_id, "full_name": name}
            tables = []
            role = p.get("role")
            if role:
                if not isinstance(role, str) or not role.strip():
                    raise ValueError
                tables.append({"table": "playing_roles", "rows": [{"name": role}]})
                player["role_id"] = {"table": "playing_roles", "name": role}
            for key, dest in (("bat", "batting_style"), ("bowl", "bowling_style")):
                value = p.get(key)
                if value not in {None, "", "--", "-"}:
                    player[dest] = value
            bats, bowls = _table(batting.data), _table(bowling.data)
            if set(bats) != set(bowls):
                raise ValueError("Batting/bowling format scopes differ.")
            formats, career = [], []
            for label, bat in bats.items():
                bowl = bowls[label]
                matches = _integer(bat["Matches"])
                if matches != _integer(bowl["Matches"]):
                    raise ValueError("Batting/bowling match totals differ.")
                if matches in {None, 0}:
                    continue
                code, family, level = FORMATS[label]
                formats.append({"code": code, "family": family, "level": level})
                innings, not_out = _integer(bat["Innings"]), _integer(bat["Not Out"])
                if innings is not None and not_out is not None and not_out > innings:
                    raise ValueError("Not-outs exceed innings.")
                dismissals = (
                    innings - not_out
                    if innings is not None and not_out is not None
                    else None
                )
                wickets, balls = _integer(bowl["Wickets"]), _integer(bowl["Balls"])
                row = {
                    "player_id": _reference("players", self.player_id),
                    "format_id": {"table": "formats", "code": code},
                    "scope": "career",
                    "matches_played": matches,
                    "batting_innings": innings,
                    "dismissals": dismissals,
                    "bowling_innings": _integer(bowl["Innings"]),
                    "wickets": wickets,
                    "legal_balls_bowled": balls,
                    "runs_conceded": _integer(bowl["Runs"]),
                }
                for source, dest in (
                    ("Runs", "runs"),
                    ("Balls", "balls_faced"),
                    ("100s", "centuries"),
                ):
                    row[dest] = _integer(bat.get(source))
                highest = bat.get("Highest")
                row["highest_score"] = _integer(
                    highest.rstrip("*") if isinstance(highest, str) else highest
                )
                row["reported_batting_average"] = _ratio(bat.get("Average"), dismissals)
                row["reported_strike_rate"] = _ratio(bat.get("SR"), row["balls_faced"])
                row["reported_bowling_average"] = _ratio(bowl.get("Avg"), wickets)
                row["reported_economy"] = _ratio(bowl.get("Eco"), balls)
                career.append(row)
            tables.extend(
                [
                    {"table": "formats", "rows": formats},
                    {"table": "players", "rows": [player]},
                    {"table": "career_stats_snapshots", "rows": career},
                ]
            )
            return decode_snapshot(
                {
                    "metadata": {
                        "schema_version": 1,
                        "provider": self.provider,
                        "provider_version": self.version,
                        "capability": "player_career",
                        "resource_key": self.player_id,
                        "fetched_at": times[-1],
                        "completeness": "partial",
                    },
                    "tables": tables,
                },
                origin="provider",
            )
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            raise APIError(
                "normalization", "Unsupported or inconsistent player career responses."
            ) from None
