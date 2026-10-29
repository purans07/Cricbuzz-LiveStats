"""Build only a missing synthetic demo database; never overwrite existing data."""

import os
from dataclasses import replace

from config import load_settings
from database.initialize import initialize_database
from services.overview import OverviewService
from utils.db_connection import Database, DatabaseError


def prepare_public_demo(environ=None):
    """Validate explicit public-sample policy before any startup initialization."""
    values = dict(os.environ if environ is None else environ)
    values.setdefault("DATA_MODE", "sample")
    values.setdefault("DATABASE_URL", "sqlite:///data/runtime/public-demo.db")
    values.setdefault("APP_ACCESS_MODE", "public_readonly")
    settings = load_settings(environ=values)
    if (
        settings.database_url
        or settings.data_mode != "sample"
        or settings.access_mode != "public_readonly"
    ):
        raise DatabaseError(
            "The demo entry point requires sample and public_readonly modes."
        )
    if not settings.database_path.exists():
        try:
            # Startup-only privilege for creating the reviewed synthetic fixture.
            # Every subsequent page receives public_readonly; no user chooses this.
            initialize_database(
                replace(settings, access_mode="local"), seed_sample=True
            )
        except FileExistsError:
            # Another startup won the atomic creation race; validate its target.
            pass
    database = Database(settings)
    try:
        OverviewService(database).read()
    finally:
        database.close()
    return settings
