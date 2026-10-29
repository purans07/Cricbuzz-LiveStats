"""Central SQLite connections and transaction boundaries for the application."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool

from config import Settings


class DatabaseError(RuntimeError):
    """Database is absent, invalid or incompatible with the selected mode."""


@contextmanager
def bootstrap_connection(path: Path):
    """Open an initializer-owned temporary file with explicit transactions."""
    connection = sqlite3.connect(str(path), isolation_level=None)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
    finally:
        connection.close()


def _open_existing(settings: Settings, readonly: bool):
    """Never create an application file implicitly; check its dataset marker."""
    uri = settings.database_path.as_uri() + ("?mode=ro" if readonly else "?mode=rw")
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5, isolation_level=None)
    except sqlite3.Error:
        raise DatabaseError(
            "Database unavailable; initialize the selected target first."
        ) from None
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        state = connection.execute(
            "SELECT mode FROM dataset_state WHERE singleton_id = 1"
        ).fetchone()
        if state is None or state[0] != settings.data_mode:
            raise DatabaseError("Database dataset mode does not match DATA_MODE.")
        if connection.execute("PRAGMA user_version").fetchone()[0] not in {1, 2}:
            raise DatabaseError("Unsupported database schema version.")
        if readonly:
            connection.execute("PRAGMA query_only = ON")
        return connection
    except (sqlite3.Error, DatabaseError) as error:
        connection.close()
        if isinstance(error, DatabaseError):
            raise
        raise DatabaseError("Database schema is unavailable or invalid.") from None


class Database:
    """Own engines, but create a fresh connection for every operation."""

    def __init__(self, settings: Settings):
        """Retain validated dependencies for this component without performing its operations."""
        self.settings = settings
        if settings.database_url:
            from database.server import server_engine

            self.writer = server_engine(settings, readonly=False)
            self.reader = server_engine(settings, readonly=True)
            return
        self.writer = self._engine(readonly=False)
        self.reader = self._engine(readonly=True)

    def _engine(self, readonly: bool):
        """Create an engine whose connections enforce the selected SQLite access policy."""
        engine = create_engine(
            "sqlite+pysqlite://",
            creator=lambda: _open_existing(self.settings, readonly),
            poolclass=NullPool,
            hide_parameters=True,
        )

        @event.listens_for(engine, "begin")
        def begin(connection):
            """Start an explicit read transaction or acquire the SQLite write transaction early."""
            connection.exec_driver_sql("BEGIN" if readonly else "BEGIN IMMEDIATE")

        return engine

    @contextmanager
    def transaction(self, *, write: bool = False):
        """Commit all changes once, bump revision on writes, or roll back."""
        if write and self.settings.access_mode != "local":
            raise DatabaseError("Writes are disabled in public_readonly mode.")
        if self.settings.database_url:
            from database.server import server_transaction

            with server_transaction(self, write=write) as connection:
                yield connection
            return
        engine = self.writer if write else self.reader
        with engine.begin() as connection:
            driver = connection.connection.driver_connection
            baseline = driver.total_changes
            yield connection
            if write and driver.total_changes > baseline:
                connection.exec_driver_sql(
                    "UPDATE dataset_state SET revision = revision + 1 "
                    "WHERE singleton_id = 1"
                )

    def close(self):
        """Dispose engine resources when finished."""
        self.writer.dispose()
        self.reader.dispose()


def schema_version(connection):
    """Read the backend-specific schema marker through the central connection layer."""
    statement = (
        "PRAGMA user_version"
        if connection.dialect.name == "sqlite"
        else "SELECT schema_version FROM dataset_state WHERE singleton_id=1"
    )
    return connection.exec_driver_sql(statement).scalar_one()


def generated_id(connection, result, table):
    """Read a generated integer ID from this connection, never MAX(id)."""
    if connection.dialect.name != "postgresql":
        return result.lastrowid
    if table in {
        "batting_performances",
        "bowling_performances",
        "fielding_performances",
    }:
        return None
    from sqlalchemy import text

    from services.ingestion import PRIMARY_IDS

    return connection.execute(
        text("SELECT currval(pg_get_serial_sequence(:table_name,:column_name))"),
        {
            "table_name": table,
            "column_name": {
                **PRIMARY_IDS,
                "sources": "source_id",
                "import_batches": "batch_id",
            }[table],
        },
    ).scalar_one()
