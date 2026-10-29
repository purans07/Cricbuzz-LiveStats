"""Read a consistent local overview without fetching or mutating records."""

from sqlalchemy import text

from database.repositories import dataset_status

OVERVIEW_SQL = """
SELECT (SELECT COUNT(*) FROM matches) AS matches,
       (SELECT COUNT(*) FROM v_active_players) AS players,
       (SELECT COUNT(*) FROM teams) AS teams,
       (SELECT COUNT(*) FROM venues) AS venues,
       (SELECT MAX(fetched_at) FROM import_batches
        WHERE status='committed') AS latest_import,
       (SELECT COUNT(*) FROM import_batches
        WHERE status='committed' AND completeness<>'complete') AS partial_imports
"""


class OverviewService:
    """Return metadata and counts in the same read-only transaction."""

    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def read(self):
        """Count stored entities; a latest import is not a live freshness claim."""
        with self.database.transaction() as connection:
            return {
                **dict(dataset_status(connection)),
                **dict(connection.execute(text(OVERVIEW_SQL)).mappings().one()),
            }
