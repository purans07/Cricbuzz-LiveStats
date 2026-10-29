"""Fetch/normalize before starting any database transaction."""

from typing import Protocol

from sqlalchemy import text

from api.adapter import Snapshot
from api.client import APIError, APIResponse
from services.ingestion import IngestionService


class ProviderNormalizer(Protocol):
    """Vendor adapters implement this only after the actual JSON is verified."""

    provider: str
    version: str

    def normalize(self, response: APIResponse) -> Snapshot:
        """Map vendor JSON into a validated provider-origin snapshot."""
        ...


class MatchService:
    """Expose refresh orchestration and stable stored-match reads."""

    def __init__(
        self, database, client=None, normalizer: ProviderNormalizer | None = None
    ):
        """Retain validated dependencies for this component without performing its operations."""
        self.database, self.client, self.normalizer = database, client, normalizer

    def refresh(self, operation, *, path_params=None, query=None):
        """Require a matching adapter; do not pretend a raw response was imported."""
        if self.client is None or self.normalizer is None:
            raise APIError(
                "configuration",
                "A verified provider client and JSON adapter are required.",
            )
        if (
            self.normalizer.provider != self.client.contract.provider
            or self.normalizer.version != self.client.contract.version
        ):
            raise APIError(
                "configuration", "Provider client and adapter versions do not match."
            )
        response = self.client.get(operation, path_params=path_params, query=query)
        if response.is_mock:
            raise APIError(
                "mock", "Gateway mock responses cannot be ingested as live data."
            )
        try:
            snapshot = self.normalizer.normalize(response)
        except APIError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError):
            raise APIError(
                "normalization", "Provider JSON adapter rejected the response."
            ) from None
        if (
            snapshot.origin != "provider"
            or snapshot.provider != response.provider
            or snapshot.provider_version != response.version
            or snapshot.fetched_at != response.fetched_at
        ):
            raise APIError(
                "provenance", "Adapter output does not match response provenance."
            )
        return IngestionService(self.database).ingest(snapshot)

    def stored_matches(self):
        """Read stored records with source/fetch metadata, without network calls."""
        with self.database.transaction() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT m.match_id,m.description,m.status,m.status_text,m.starts_at,"
                        "s.name AS source,b.fetched_at,b.completeness FROM matches m "
                        "LEFT JOIN sources s ON s.source_id=m.source_id "
                        "LEFT JOIN import_batches b ON b.batch_id=m.last_batch_id ORDER BY m.match_id"
                    )
                ).mappings()
            ]
