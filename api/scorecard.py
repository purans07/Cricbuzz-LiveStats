"""Regular v2 scorecards, mapped using the already verified match participants."""

from datetime import UTC, datetime

from api.adapter import decode_snapshot
from api.client import APIError, APIResponse
from api.cricbuzz_v2 import _balls, _id, _reference


def _count(value):
    """Require a nonnegative integer statistic; reject unknown or malformed counts."""
    if type(value) is not int or value < 0:
        raise ValueError("Invalid scorecard count.")
    return value


class CricbuzzV2ScorecardNormalizer:
    """Require stored participant identities; never infer teams from innings order."""

    provider = "cricketapilive-cricbuzz-cricket"
    version = "v2"

    def __init__(self, match_id, teams):
        """Retain validated dependencies for this component without performing its operations."""
        self.match_id = _id(match_id)
        # teams maps full provider team names to their provider identifiers.
        self.teams = {name: _id(tid) for name, tid in teams.items()}
        if len(self.teams) != 2 or len(set(self.teams.values())) != 2:
            raise ValueError("Two distinct verified match participants are required.")

    def normalize(self, response: APIResponse):
        """Validate provider provenance and map supported response fields into a snapshot."""
        if (
            response.provider != self.provider
            or response.version != self.version
            or response.operation != "match_scorecard"
            or response.is_mock
        ):
            raise APIError(
                "provenance", "Response does not match the scorecard adapter."
            )
        try:
            data = response.data
            # Captured regular scorecards include the match identifier in this URL.
            url = data["appindex"]["weburl"]
            if f"/live-cricket-scorecard/{self.match_id}/" not in url:
                raise ValueError("Scorecard belongs to another match.")
            innings = data["scorecard"]
            if not isinstance(innings, list) or not innings:
                raise ValueError
            records = {
                t: {}
                for t in (
                    "players",
                    "match_players",
                    "innings",
                    "batting_performances",
                    "bowling_performances",
                )
            }
            mid = _reference("matches", self.match_id)
            for inning in innings:
                number = int(_id(inning["inningsid"]))
                if number in records["innings"]:
                    raise ValueError
                batting = self.teams[inning["batteamname"]]
                bowling = next(t for t in self.teams.values() if t != batting)
                records["innings"][number] = {
                    "match_id": mid,
                    "innings_number": number,
                    "batting_team_id": _reference("teams", batting),
                    "bowling_team_id": _reference("teams", bowling),
                    "total_runs": _count(inning["score"]),
                    "wickets": _count(inning["wickets"]),
                    "legal_balls": _balls(inning["overs"]),
                }
                ref = {
                    "table": "innings",
                    "match_external_id": self.match_id,
                    "innings_number": number,
                }
                for kind, team in (("batsman", batting), ("bowler", bowling)):
                    people = inning[kind]
                    if not isinstance(people, list):
                        raise ValueError
                    seen = set()
                    for position, person in enumerate(people, 1):
                        pid = _id(person["id"])
                        if pid in seen:
                            raise ValueError
                        seen.add(pid)
                        name = person["name"]
                        if not isinstance(name, str) or not name.strip():
                            raise ValueError
                        previous = records["players"].get(pid)
                        if previous and previous["full_name"] != name:
                            raise ValueError
                        records["players"][pid] = {
                            "external_id": pid,
                            "full_name": name,
                        }
                        base = {
                            "innings_id": ref,
                            "match_id": mid,
                            "player_id": _reference("players", pid),
                            "team_id": _reference("teams", team),
                        }
                        if kind == "batsman":
                            dismissal = person["outdec"].strip()
                            runs, balls = (
                                _count(person["runs"]),
                                _count(person["balls"]),
                            )
                            # Empty zero rows are a did-not-bat roster, not batting innings.
                            if not dismissal and not runs and not balls:
                                continue
                            if not dismissal:
                                raise ValueError("Ambiguous batting participation.")
                            if dismissal.lower() in {
                                "not out",
                                "batting",
                                "retired hurt",
                                "retd hurt",
                            }:
                                dismissed = 0
                            elif dismissal.lower().startswith(
                                (
                                    "b ",
                                    "c ",
                                    "c & b ",
                                    "lbw ",
                                    "st ",
                                    "run out",
                                    "hit wicket",
                                    "retired out",
                                    "obstructing the field",
                                )
                            ):
                                dismissed = 1
                            else:
                                raise ValueError("Unsupported dismissal.")
                            records["batting_performances"][(number, pid)] = {
                                **base,
                                "batting_position": position,
                                "runs": runs,
                                "balls_faced": balls,
                                "fours": _count(person["fours"]),
                                "sixes": _count(person["sixes"]),
                                "is_dismissed": dismissed,
                                "dismissal_text": dismissal,
                            }
                        else:
                            records["bowling_performances"][(number, pid)] = {
                                **base,
                                "legal_balls": _balls(person["overs"]),
                                "runs_conceded": _count(person["runs"]),
                                "wickets": _count(person["wickets"]),
                                "maidens": _count(person["maidens"]),
                            }
                        participant = {
                            "match_id": mid,
                            "player_id": _reference("players", pid),
                            "team_id": _reference("teams", team),
                            "participation": "observed",
                        }
                        prior = records["match_players"].get(pid)
                        if prior and prior != participant:
                            raise ValueError("Player appears for both teams.")
                        records["match_players"][pid] = participant
            updated = data["responselastupdated"]
            if type(updated) not in {str, int} or not str(updated).isdigit():
                raise ValueError
            return decode_snapshot(
                {
                    "metadata": {
                        "schema_version": 1,
                        "provider": self.provider,
                        "provider_version": self.version,
                        "capability": response.operation,
                        "resource_key": self.match_id,
                        "fetched_at": response.fetched_at,
                        "upstream_updated_at": datetime.fromtimestamp(
                            int(updated), UTC
                        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "completeness": "partial",
                    },
                    "tables": [
                        {"table": table, "rows": list(rows.values())}
                        for table, rows in records.items()
                    ],
                },
                origin="provider",
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            OverflowError,
            OSError,
        ):
            raise APIError(
                "normalization", "Unsupported or malformed scorecard."
            ) from None
