"""Normalize verified series match maps using an explicitly reviewed competition scope."""

from dataclasses import replace

from api.adapter import decode_snapshot
from api.client import APIError
from api.cricbuzz_v2 import CricbuzzV2MatchListNormalizer, _id


class CricbuzzV2SeriesNormalizer:
    """Preserve series identity and require scope instead of guessing international status."""

    provider = "cricketapilive-cricbuzz-cricket"
    version = "v2"

    def __init__(self, series_id, scope):
        """Validate the provider series ID and operator-reviewed list category."""
        self.series_id = _id(series_id)
        if scope not in {"International", "Domestic", "League", "Women"}:
            raise ValueError("Select a verified series competition scope.")
        self.scope = scope

    def normalize(self, response):
        """Map supported matchDetailsMap entries and ignore explicit advertisement wrappers."""
        if (
            response.provider,
            response.version,
            response.operation,
            response.is_mock,
        ) != (self.provider, self.version, "series_matches", False):
            raise APIError("provenance", "Response does not match the series adapter.")
        try:
            entries = response.data["matchDetails"]
            if not isinstance(entries, list):
                raise ValueError
            matches = []
            for entry in entries:
                if set(entry) == {"adDetail"}:
                    continue
                wrapper = entry["matchDetailsMap"]
                if _id(wrapper["seriesId"]) != self.series_id or not isinstance(
                    wrapper["match"], list
                ):
                    raise ValueError
                matches.extend(wrapper["match"])
            if not matches:
                raise ValueError
            name = matches[0]["matchInfo"]["seriesName"]
            payload = {
                "typeMatches": [
                    {
                        "matchType": self.scope,
                        "seriesMatches": [
                            {
                                "seriesAdWrapper": {
                                    "seriesId": self.series_id,
                                    "seriesName": name,
                                    "matches": matches,
                                }
                            }
                        ],
                    }
                ]
            }
            snapshot = CricbuzzV2MatchListNormalizer().normalize(
                replace(response, operation="recent_matches", data=payload)
            )
            return decode_snapshot(
                {
                    "metadata": {
                        "schema_version": 1,
                        "provider": self.provider,
                        "provider_version": self.version,
                        "capability": "series_matches",
                        "resource_key": self.series_id,
                        "fetched_at": response.fetched_at,
                        "completeness": "partial",
                    },
                    "tables": list(snapshot.groups),
                },
                origin="provider",
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise APIError(
                "normalization", "Unsupported or malformed series match response."
            ) from None
