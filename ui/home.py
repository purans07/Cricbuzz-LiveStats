"""Home page presentation, local overview and bundled learning guides."""

import logging
import re

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import PROJECT_ROOT, ConfigurationError, load_settings
from services.overview import OverviewService
from ui.preferences import apply_preferences
from utils.dates import display_timestamp
from utils.db_connection import Database, DatabaseError

LOGGER = logging.getLogger(__name__)
GUIDES = {
    "Project guide": "README.md",
    "Folder structure": "documentation/folder_guide.md",
    "Database setup": "documentation/database_setup.md",
    "API setup": "documentation/api_setup.md",
    "SQL lessons": "sql/queries/README.md",
}
PAGE_ROADMAP = (
    ("Home", "Project guide and saved-data overview", "Ready"),
    ("Live Matches", "Match status and detailed scorecards", "Ready"),
    ("Top Players", "Batting and bowling career statistics", "Ready"),
    ("Analytics", "Explore the 26 SQL analyses", "Ready"),
    ("CRUD", "Manage players and match statistics", "Ready"),
    ("Settings", "Review data and display preferences", "Ready"),
)


def read_guide(name):
    """Resolve bundled documentation through a fixed allowlist."""
    return (PROJECT_ROOT / GUIDES[name]).read_text(encoding="utf-8")


def guide_preview(content):
    """Render bundled Markdown without source-tree links becoming app routes."""
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
        st.error("The data settings need attention. Review the setup guide below.")
        return
    except (DatabaseError, SQLAlchemyError, OSError):
        # Never include exceptions, database URLs or credential values in the UI/log.
        LOGGER.warning("Home overview unavailable; review local database setup.")
        st.warning(
            "Saved data is unavailable. Check that the selected database exists "
            "and matches your data mode. The project guides are still available below."
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
    st.caption(
        f"Access: {'Read only' if settings.access_mode == 'public_readonly' else 'Local operator'} "
        f"· Dataset revision {overview['revision']} · Display timezone: {settings.display_timezone}"
    )


def render_home():
    """Render the project overview and bundled operational guides."""
    st.caption("CRICBUZZ LIVESTATS / PROJECT HOME")
    st.title("Cricket insights, one innings at a time.")
    st.write(
        "Follow match snapshots, understand player performance and explore the "
        "SQL behind the numbers—all in one guided cricket analytics project."
    )
    st.caption("Python · Streamlit · SQLite · SQLAlchemy · REST API · pandas · Plotly")
    _render_overview()
    st.divider()
    st.subheader("Explore the project")
    st.write(
        "Explore matches, compare players and investigate performance with 26 saved SQL analyses."
    )
    columns = st.columns(3)
    for index, (title, description, status) in enumerate(PAGE_ROADMAP):
        with columns[index % 3].container(border=True):
            st.markdown(f"**{title}**")
            st.write(description)
            st.caption(status)
    st.subheader("Start here")
    st.markdown(
        "1. Check the sample or live-source label above before reading any figures.\n"
        "2. Use the guides below to review setup, project folders and SQL lessons.\n"
        "3. Open any of the six pages from the sidebar.\n"
        "4. Refresh provider data explicitly from Live Matches; browsing uses saved data."
    )
    st.subheader("Project documentation")
    for title in GUIDES:
        with st.expander(title):
            try:
                content = read_guide(title)
            except OSError:
                st.warning("This bundled guide is unavailable in this installation.")
                continue
            st.download_button(
                "Download guide",
                data=content,
                file_name=GUIDES[title].split("/")[-1],
                mime="text/markdown",
                key=f"guide_{title}",
                on_click="ignore",
            )
            st.markdown(guide_preview(content))
    st.caption(
        "Explore career comparisons in Top Players and performance charts in Analytics."
    )
