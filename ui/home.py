"""Visitor-focused Home page and saved dataset overview."""

import logging
import re

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import ConfigurationError, load_settings
from services.overview import OverviewService
from ui.preferences import apply_preferences
from utils.dates import display_timestamp
from utils.db_connection import Database, DatabaseError

LOGGER = logging.getLogger(__name__)


def guide_preview(content):
    """Keep lesson document links from becoming invalid application routes."""
    return re.sub(r"\[([^\]]+)\]\((?!https?://|#)[^)]+\)", r"\1", content)


def _overview():
    """Read selected settings and dispose connections even after a failure."""
    settings = apply_preferences(load_settings())
    database = Database(settings)
    try:
        return settings, OverviewService(database).read()
    finally:
        database.close()


def _render_overview():
    """Separate unavailable data from real zero counts and sample from live."""
    st.subheader("Your saved dataset")
    st.button(
        "Reload saved overview",
        help="Read the selected local database again. No API request is made.",
        key="reload_overview",
    )
    try:
        settings, overview = _overview()
    except ConfigurationError:
        st.error(
            "The data settings need attention. Check the data connection in Settings."
        )
        return
    except (DatabaseError, SQLAlchemyError, OSError):
        # Never include exceptions, database URLs or credential values in the UI/log.
        LOGGER.warning("Home overview unavailable; review local database setup.")
        st.warning(
            "Saved data is unavailable. Check that the selected database exists "
            "and matches your data mode. You can still explore the pages below."
        )
        return
    if overview["mode"] == "sample":
        st.info("SAMPLE DATA · Fictional training records for learning and testing.")
    else:
        st.info(
            "LIVE DATA SOURCE · Saved provider records. Opening Home does not "
            "fetch current scores."
        )
    columns = st.columns(4)
    for column, label, key in zip(
        columns,
        ("Stored matches", "Active players", "Teams", "Venues"),
        ("matches", "players", "teams", "venues"),
        strict=True,
    ):
        column.metric(label, overview[key])
    timestamp = overview["latest_import"]
    if timestamp:
        try:
            timestamp = display_timestamp(timestamp, settings.display_timezone)
        except ValueError:
            timestamp = "Time unavailable"
        st.caption(
            f"Latest committed import: {timestamp}. This is an import time, not a live-check time."
        )
    else:
        st.caption(
            "No committed imports yet. Counts describe only the records stored here."
        )
    if overview["partial_imports"]:
        st.caption(
            "Some committed imports have partial or unknown coverage. "
            "Stored counts and SQL results do not represent all cricket history."
        )


def render_home():
    """Welcome visitors with dataset context and direct routes to core features."""
    st.title("Cricket insights, one innings at a time.")
    st.write(
        "Explore match scorecards, compare players and discover the stories behind cricket performance."
    )
    _render_overview()
    st.divider()
    st.subheader("Explore cricket")
    destinations = (
        (
            "Live Matches",
            "Explore saved matches and detailed innings scorecards.",
            "pages/02_Live_Matches.py",
            "View matches",
        ),
        (
            "Top Players",
            "Compare batting and bowling career statistics.",
            "pages/03_Top_Players.py",
            "Compare players",
        ),
        (
            "Analytics",
            "Investigate performance with 26 saved analyses and charts.",
            "pages/04_Analytics.py",
            "Explore analytics",
        ),
    )
    for column, (title, description, path, label) in zip(
        st.columns(3), destinations, strict=True
    ):
        with column.container(border=True):
            st.subheader(title)
            st.write(description)
            st.page_link(path, label=label)
    st.subheader("Get started")
    st.markdown(
        "1. Check the dataset label to see whether you are viewing sample or saved provider data.\n"
        "2. Open Matches, Players or Analytics above and use the filters to explore.\n"
        "3. Check the import time when assessing freshness. Browsing uses saved data."
    )
