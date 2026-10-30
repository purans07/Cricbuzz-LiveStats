"""Match-list mapping based on the user's captured cricketapilive v2 response."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from api.adapter import decode_snapshot
from api.client import APIError, APIResponse


def _id(value):
    """Require a nonempty positive provider identifier, represented as text."""
    if type(value) not in {int, str} or not str(value).isdigit() or int(value) <= 0:
        raise ValueError("Invalid provider identifier.")
    return str(value)


def _milliseconds(value):
    """Convert captured start/series timestamps, whose documented field unit is ms."""
    if type(value) not in {str, int} or not str(value).isdigit():
        raise ValueError("Invalid epoch milliseconds.")
    return datetime.fromtimestamp(int(value) / 1000, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _balls(value):
    """Interpret captured overs as O.B, permitting B=6 as a completed over."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Invalid provider overs.")
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0:
            raise ValueError
        whole = int(number)
        suffix = (number - whole) * 10
        if suffix != int(suffix) or not 0 <= suffix <= 6:
            raise ValueError
        return whole * 6 + int(suffix)
    except (InvalidOperation, OverflowError):
        raise ValueError("Invalid provider overs.") from None


def _reference(table, external_id):
    """Build a typed normalized reference using the provider external identifier."""
    return {"table": table, "external_id": external_id}


class CricbuzzV2MatchListNormalizer:
    """Map only observed list fields; scorecards/profiles need separate captures."""

    provider = "cricketapilive-cricbuzz-cricket"
    version = "v2"

    def normalize(self, response: APIResponse):
        """Normalize the observed list structure without inventing missing details."""
        if (
            response.provider != self.provider
            or response.version != self.version
            or response.operation
            not in {"live_matches", "recent_matches", "upcoming_matches"}
            or response.is_mock
        ):
            raise APIError(
                "provenance", "Response does not match this provider/list adapter."
            )
        try:
            payload = response.data
            if not isinstance(payload, dict) or not isinstance(
                payload.get("typeMatches"), list
            ):
                raise ValueError
            records = {
                name: {}
                for name in (
                    "formats",
                    "teams",
                    "venues",
                    "series",
                    "series_formats",
                    "matches",
                    "match_teams",
                    "innings",
                )
            }
            for category in payload["typeMatches"]:
                scope = category["matchType"]
                if scope not in {"International", "Domestic", "League", "Women"}:
                    raise ValueError
                if not isinstance(category["seriesMatches"], list):
                    raise ValueError
                for wrapper in category["seriesMatches"]:
                    if "seriesAdWrapper" not in wrapper:
                        if set(wrapper) == {"ad"}:
                            continue
                        raise ValueError
                    series = wrapper["seriesAdWrapper"]
                    sid = _id(series["seriesId"])
                    if not isinstance(series["matches"], list):
                        raise ValueError
                    for match in series["matches"]:
                        info = match["matchInfo"]
                        mid = _id(info["matchId"])
                        if _id(info["seriesId"]) != sid or mid in records["matches"]:
                            raise ValueError
                        raw_format = info["matchFormat"]
                        if raw_format not in {"TEST", "ODI", "T20"}:
                            raise ValueError
                        # T20 is not silently promoted to official T20I status.
                        description = info["matchDesc"]
                        is_warmup = (
                            "warm" in description.lower()
                            and "up" in description.lower()
                        )
                        if is_warmup:
                            code = f"{scope.upper()}_WARMUP_{raw_format}"
                        elif scope == "International" and raw_format in {"TEST", "ODI"}:
                            code = raw_format
                        else:
                            code = f"{scope.upper()}_{raw_format}"
                        level = (
                            "international"
                            if scope == "International"
                            else (
                                "domestic"
                                if scope in {"Domestic", "League"}
                                else "other"
                            )
                        )
                        records["formats"][code] = {
                            "code": code,
                            "family": "OTHER" if is_warmup else raw_format,
                            "level": "other" if is_warmup else level,
                        }
                        series_row = records["series"].setdefault(
                            sid,
                            {
                                "external_id": sid,
                                "name": series["seriesName"],
                            },
                        )
                        for field, destination in (
                            ("seriesStartDt", "start_date"),
                            ("seriesEndDt", "end_date"),
                        ):
                            if info.get(field) is not None:
                                series_row[destination] = _milliseconds(info[field])[
                                    :10
                                ]
                        records["series_formats"][(sid, code)] = {
                            "series_id": _reference("series", sid),
                            "format_id": {"table": "formats", "code": code},
                        }
                        teams = []
                        for position in (1, 2):
                            team = info[f"team{position}"]
                            tid = _id(team["teamId"])
                            teams.append(tid)
                            existing = records["teams"].get(tid)
                            row = {
                                "external_id": tid,
                                "name": team["teamName"],
                                "is_international": int(scope == "International"),
                            }
                            if existing:
                                if existing["name"] != row["name"]:
                                    raise ValueError
                                # The same national side can also appear in a league
                                # wrapper; observed international identity takes precedence.
                                row["is_international"] = max(
                                    existing["is_international"],
                                    row["is_international"],
                                )
                            records["teams"][tid] = row
                            records["match_teams"][(mid, tid)] = {
                                "match_id": _reference("matches", mid),
                                "team_id": _reference("teams", tid),
                                "slot": position,
                            }
                        if teams[0] == teams[1]:
                            raise ValueError
                        state = info.get("state", "").strip().lower()
                        status = {
                            "stumps": "live",
                            "lunch": "live",
                            "tea": "live",
                            "toss": "live",
                            "in progress": "live",
                            "innings break": "live",
                            "live": "live",
                            "complete": "completed",
                            "completed": "completed",
                            "preview": "scheduled",
                            "upcoming": "scheduled",
                            "abandon": "abandoned",
                            "abandoned": "abandoned",
                        }.get(state, "unknown")
                        row = {
                            "external_id": mid,
                            "description": info["matchDesc"],
                            "series_id": _reference("series", sid),
                            "format_id": {"table": "formats", "code": code},
                            "status": status,
                            "status_text": info.get("status"),
                        }
                        if info.get("startDate") is not None:
                            row["starts_at"] = _milliseconds(info["startDate"])
                        # endDate is scheduled; never claim it is actual completion.
                        venue = info.get("venueInfo")
                        if venue is not None:
                            vid = _id(venue["id"])
                            records["venues"][vid] = {
                                "external_id": vid,
                                "name": venue["ground"],
                                "city": venue.get("city"),
                            }
                            row["venue_id"] = _reference("venues", vid)
                        records["matches"][mid] = row
                        scores = match.get("matchScore", {})
                        if not isinstance(scores, dict) or set(scores) - {
                            "team1Score",
                            "team2Score",
                        }:
                            raise ValueError
                        for position, tid in enumerate(teams, 1):
                            score = scores.get(f"team{position}Score", {})
                            if not isinstance(score, dict):
                                raise ValueError
                            for summary in score.values():
                                number = int(_id(summary["inningsId"]))
                                key = (mid, number)
                                if key in records["innings"]:
                                    raise ValueError
                                inning = {
                                    "match_id": _reference("matches", mid),
                                    "innings_number": number,
                                    "batting_team_id": _reference("teams", tid),
                                    "bowling_team_id": _reference(
                                        "teams", teams[2 - position]
                                    ),
                                }
                                for field in ("runs", "wickets"):
                                    if summary.get(field) is not None:
                                        if (
                                            type(summary[field]) is not int
                                            or summary[field] < 0
                                        ):
                                            raise ValueError
                                        inning[
                                            "total_runs" if field == "runs" else field
                                        ] = summary[field]
                                if summary.get("overs") is not None:
                                    inning["legal_balls"] = _balls(summary["overs"])
                                records["innings"][key] = inning
            upstream = payload.get("responseLastUpdated")
            if upstream is not None:
                if type(upstream) not in {str, int} or not str(upstream).isdigit():
                    raise ValueError
                upstream = datetime.fromtimestamp(int(upstream), UTC).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            normalized = {
                "metadata": {
                    "schema_version": 1,
                    "provider": self.provider,
                    "provider_version": self.version,
                    "capability": response.operation,
                    "resource_key": "list",
                    "fetched_at": response.fetched_at,
                    "upstream_updated_at": upstream,
                    "completeness": "partial",
                },
                "tables": [
                    {"table": table, "rows": list(rows.values())}
                    for table, rows in records.items()
                ],
            }
            return decode_snapshot(normalized, origin="provider")
        except (
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            OverflowError,
            OSError,
        ):
            raise APIError(
                "normalization",
                "Provider match list contains an unsupported or malformed record.",
            ) from None
