"""Offline checks for configuration, SQL translation and server query boundaries."""

import pytest
from sqlglot import parse_one

from config import ConfigurationError, load_settings
from database.server import dialect_sql, validate_read
from services.analytics import QUESTIONS, SAFE_FUNCTIONS, saved_sql


@pytest.mark.parametrize(
    "backend,driver,port",
    [("postgresql", "psycopg", 55432), ("mysql", "pymysql", 53306)],
)
def test_server_config_hides_credentials_and_requires_distinct_reader(
    backend, driver, port
):
    values = {
        "DATABASE_URL": f"{backend}+{driver}://writer:private-test-value@127.0.0.1:{port}/cricbuzz_test",
        "READ_DATABASE_URL": f"{backend}+{driver}://reader:private-test-value@127.0.0.1:{port}/cricbuzz_test",
    }
    settings = load_settings(environ=values)
    assert settings.database_url and settings.read_database_url
    assert "private-test-value" not in repr(settings)
    with pytest.raises(ConfigurationError):
        load_settings(environ={"DATABASE_URL": values["DATABASE_URL"]})
    with pytest.raises(ConfigurationError):
        load_settings(environ={**values, "READ_DATABASE_URL": values["DATABASE_URL"]})


@pytest.mark.parametrize("query", [q.id for q in QUESTIONS])
@pytest.mark.parametrize("dialect", ["postgresql", "mysql"])
def test_all_reviewed_queries_compile_for_server(query, dialect):
    translated = dialect_sql(saved_sql(query), dialect)
    assert parse_one(
        translated, read="postgres" if dialect == "postgresql" else "mysql"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM players",
        "SELECT 1; SELECT 2",
        "SELECT pg_sleep(10)",
        "SELECT load_file('/etc/passwd')",
        "SELECT * INTO x FROM players",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM other.players",
        "SELECT @@version",
        "WITH x AS (DELETE FROM players RETURNING *) SELECT * FROM x",
    ],
)
def test_server_custom_query_rejects_side_effects_and_external_tables(sql):
    with pytest.raises(ValueError):
        validate_read(sql, {"players"}, SAFE_FUNCTIONS)


def test_server_custom_select_and_integer_quarter_translation():
    validate_read(
        "SELECT full_name FROM players WHERE player_id>0", {"players"}, SAFE_FUNCTIONS
    )
    assert "FLOOR(" in dialect_sql(saved_sql("Q25"), "mysql")
