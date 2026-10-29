"""Validated local settings; credentials are never included in error messages."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

PROJECT_ROOT = Path(__file__).resolve().parent


class ConfigurationError(ValueError):
    """Settings are missing, unsupported or unsafe for the selected mode."""


@dataclass(frozen=True)
class Settings:
    """Validated settings used by database operations."""

    data_mode: str
    database_path: Path
    display_timezone: str = "Asia/Kolkata"
    access_mode: str = "local"
    database_url: str | None = field(default=None, repr=False)
    read_database_url: str | None = field(default=None, repr=False)


def read_environment(environ=None, env_file=None) -> dict:
    """Load private .env with process overrides; explicit mappings isolate tests."""
    if environ is not None:
        return dict(environ)
    values = dict(dotenv_values(env_file or PROJECT_ROOT / ".env"))
    values.update(os.environ)
    return values


def load_settings(
    environ: Mapping[str, str] | None = None,
    env_file: Path | None = None,
) -> Settings:
    """Load .env then environment overrides; explicit mappings isolate tests."""
    values = read_environment(environ, env_file)
    mode = values.get("DATA_MODE", "sample")
    if mode not in {"sample", "live"}:
        raise ConfigurationError("DATA_MODE must be sample or live.")
    raw_url = values.get("DATABASE_URL", f"sqlite:///data/runtime/{mode}.db")
    try:
        url = make_url(raw_url)
    except (ArgumentError, TypeError, ValueError):
        raise ConfigurationError("DATABASE_URL is not a valid database URL.") from None
    backend = url.get_backend_name()
    server_url = reader_url = None
    if backend == "sqlite":
        if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
            raise ConfigurationError("Unsupported SQLite driver.")
        if url.query or url.host or url.username or url.password:
            raise ConfigurationError(
                "SQLite URL must name a local file without options."
            )
        if not url.database or url.database == ":memory:":
            raise ConfigurationError("Configure a persistent SQLite file.")
        path = Path(url.database).expanduser()
        path = (
            (PROJECT_ROOT / path).resolve()
            if not path.is_absolute()
            else path.resolve()
        )
    elif backend in {"postgresql", "mysql"}:
        expected = {"postgresql": "postgresql+psycopg", "mysql": "mysql+pymysql"}[
            backend
        ]
        if (
            url.drivername not in {backend, expected}
            or not url.host
            or not url.database
            or not url.username
            or set(url.query)
            - (
                {"sslmode", "sslrootcert", "sslcert", "sslkey"}
                if backend == "postgresql"
                else {
                    "ssl_ca",
                    "ssl_cert",
                    "ssl_key",
                    "ssl_verify_cert",
                    "ssl_verify_identity",
                }
            )
        ):
            raise ConfigurationError(
                "Configure a supported server URL without query options."
            )
        server_url = url.set(drivername=expected).render_as_string(hide_password=False)
        try:
            reader = make_url(values.get("READ_DATABASE_URL", ""))
        except (ArgumentError, TypeError, ValueError):
            raise ConfigurationError(
                "A separate SELECT-only READ_DATABASE_URL is required."
            ) from None
        if (
            (reader.get_backend_name(), reader.host, reader.port, reader.database)
            != (backend, url.host, url.port, url.database)
            or reader.username == url.username
            or set(reader.query)
            - (
                {"sslmode", "sslrootcert", "sslcert", "sslkey"}
                if backend == "postgresql"
                else {
                    "ssl_ca",
                    "ssl_cert",
                    "ssl_key",
                    "ssl_verify_cert",
                    "ssl_verify_identity",
                }
            )
        ):
            raise ConfigurationError(
                "The reader must be a distinct SELECT-only account on the same database."
            )
        reader_url = reader.set(drivername=expected).render_as_string(
            hide_password=False
        )
        path = PROJECT_ROOT / "data/runtime" / f"{mode}.db"
    else:
        raise ConfigurationError(
            "Supported databases are SQLite, PostgreSQL and MySQL."
        )
    timezone = values.get("DISPLAY_TIMEZONE", "Asia/Kolkata")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ConfigurationError("DISPLAY_TIMEZONE must be a known timezone.") from None
    access = values.get("APP_ACCESS_MODE", "local")
    if access not in {"local", "public_readonly"}:
        raise ConfigurationError("APP_ACCESS_MODE must be local or public_readonly.")
    return Settings(mode, path, timezone, access, server_url, reader_url)
