"""Public sample-demo entry point; local administration continues through main.py."""

import os
import runpy

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import PROJECT_ROOT, ConfigurationError
from deployment.public_demo import prepare_public_demo
from utils.db_connection import DatabaseError


def main():
    """Prepare an isolated readonly sample and launch the shared dashboard."""
    try:
        settings = prepare_public_demo()
    except (ConfigurationError, DatabaseError, SQLAlchemyError, OSError, ValueError):
        st.error(
            "The read-only sample demo could not start. Check deployment settings and writable startup storage. No existing database was replaced."
        )
        st.stop()
    os.environ.update(
        DATA_MODE="sample",
        APP_ACCESS_MODE="public_readonly",
        DATABASE_URL="sqlite:///" + str(settings.database_path),
        DISPLAY_TIMEZONE=settings.display_timezone,
    )
    runpy.run_path(str(PROJECT_ROOT / "main.py"), run_name="__main__")


if __name__ == "__main__":
    main()
