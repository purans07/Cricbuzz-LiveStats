"""Safe local health and configuration summaries with no network requests."""

from sqlalchemy.exc import SQLAlchemyError

from api.client import APIError
from api.configuration import load_api_settings
from services.overview import OverviewService
from utils.db_connection import Database, DatabaseError, schema_version


def database_health(settings):
    """Inspect an existing target read-only; never create, migrate or repair it."""
    database = Database(settings)
    try:
        overview = OverviewService(database).read()
        with database.transaction() as c:
            schema = schema_version(c)
        return {"available": True, "schema_version": schema, **overview}
    except (DatabaseError, SQLAlchemyError, OSError):
        return {"available": False}
    finally:
        database.close()


def api_readiness(loader=None):
    """Return only allowlisted non-secret values; configured is not authenticated."""
    try:
        api = (loader or load_api_settings)()
        return {
            "configured": True,
            "provider": api.contract.provider,
            "version": api.contract.version,
            "connect_timeout": api.policy.connect_timeout,
            "read_timeout": api.policy.read_timeout,
            "max_attempts": api.policy.max_attempts,
            "operation_budget": api.policy.operation_budget,
            "minimum_interval": api.policy.min_interval,
        }
    except (APIError, OSError, ValueError, TypeError):
        return {"configured": False}
