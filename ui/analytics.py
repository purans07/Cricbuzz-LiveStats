"""Saved SQL lessons and a restricted local custom-query workspace."""

from dataclasses import replace
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import PROJECT_ROOT, ConfigurationError, load_settings
from services.analytics import (
    QUESTIONS,
    AnalyticsError,
    AnalyticsService,
    parameters,
    question,
    saved_sql,
)
from ui.home import guide_preview
from ui.preferences import apply_preferences
from ui.visualizations import render_visualizations
from utils.db_connection import Database, DatabaseError


def _result(result):
    """Display bounded query rows and their committed database snapshot context."""
    st.caption(
        f"{len(result['rows'])} displayed rows · Dataset revision {result['revision']}"
    )
    if result["truncated"]:
        st.warning(
            "Output was truncated at the selected row cap or 1 MB result budget. Narrow your query to see a complete result."
        )
    if result["rows"]:
        st.dataframe(
            pd.DataFrame(result["rows"], columns=result["columns"]),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info(
            "No rows returned. This can mean no qualifying records or insufficient saved coverage; it is not proof of no real-world cricket history."
        )


def _saved(service):
    """Render a reviewed question, its lesson and explicitly submitted parameters."""
    selected = st.selectbox(
        "SQL question",
        [q.id for q in QUESTIONS],
        format_func=lambda key: f"{key} · {question(key).title}",
        key="analytics_question",
    )
    q = question(selected)
    st.subheader(f"{q.id} · {q.title}")
    st.caption(
        "Each lesson documents definitions, missing-data rules, limitations and optimization. Some SQL has fixed historical scope; only named parameters below change with the analysis date."
    )
    if q.id in {"Q13", "Q24"}:
        st.warning(
            "Adjacent batting-position combined scores are a proxy, not measured runs during an actual shared stand."
        )
    if q.id in {"Q21", "Q23", "Q25"}:
        st.caption(
            "Scores, form labels and trend phases use the documented teaching rules; they are not validated predictions."
        )
    with st.expander("Lesson and interpretation"):
        st.markdown(
            guide_preview((PROJECT_ROOT / "documentation" / q.lesson).read_text())
        )
    venue = (
        st.radio(
            "Q22 output",
            ["Pair summary", "Venue breakdown"],
            key="analytics_q22_output",
        )
        == "Venue breakdown"
        if q.id == "Q22"
        else False
    )
    sql = saved_sql(selected, venue_breakdown=venue)
    with st.expander("SQL to execute", expanded=False):
        st.code(sql, language="sql")
    with st.form("saved_analytics"):
        day = st.date_input(
            "Analysis date (UTC)",
            value=date(2026, 10, 1),
            min_value=date(2000, 1, 1),
            max_value=date(2100, 12, 31),
            key="analytics_date",
        )
        st.caption(
            "Dates bind midnight UTC. Q02 uses the preceding 30 days; Q22 the preceding three calendar years; Q25 the preceding twelve completed quarters. See the lesson for exact inclusivity."
        )
        source = None
        if "source_name" in q.parameters:
            sources = service.sources()
            if not sources:
                st.info("No statistics sources are stored yet.")
            else:
                source = st.selectbox(
                    "Statistics source", sources, key="analytics_source"
                )
        limit = st.selectbox(
            "Maximum displayed rows", [50, 100, 500], index=2, key="analytics_limit"
        )
        submit = st.form_submit_button("Run saved question")
    st.caption(
        "Sample lessons use 2026-10-01 for reproducible results. Live snapshots may be old or incomplete; choosing today does not fetch new records."
    )
    if submit:
        try:
            st.write("Bound parameters")
            st.json(parameters(selected, day.isoformat(), source))
            _result(
                service.run_saved(
                    selected,
                    day.isoformat(),
                    source,
                    venue_breakdown=venue,
                    row_limit=limit,
                )
            )
        except AnalyticsError as error:
            st.warning(str(error))


def _custom(service):
    """Render the restricted local SQL workspace and its explicitly submitted results."""
    if service.database.settings.access_mode != "local":
        st.info(
            "Custom SQL is disabled in read-only visitor mode. Saved questions remain available."
        )
        return
    st.caption(
        "One read statement · 2-second execution budget · maximum 500 rows / 1 MB output · no writes, attachments, pragmas or extension/file functions. Queries run only when submitted."
    )
    with st.expander("Dataset tables and views"):
        for item in service.schema():
            st.code(item["sql"], language="sql")
    with st.form("custom_analytics"):
        sql = st.text_area(
            "Read-only SQL",
            value="SELECT full_name, batting_style FROM v_active_players ORDER BY player_id LIMIT 10;",
            height=180,
            max_chars=20000,
            key="custom_sql",
        )
        limit = st.selectbox(
            "Maximum displayed rows", [50, 100, 500], index=0, key="custom_limit"
        )
        submit = st.form_submit_button("Run custom query")
    if submit:
        try:
            _result(service.run_custom(sql, row_limit=limit))
        except AnalyticsError as error:
            st.warning(str(error))


def render_analytics():
    """Route the selected saved dataset to queries or analytical visualizations."""
    st.caption("CRICBUZZ LIVESTATS / SQL WORKSPACE")
    st.title("Analytics")
    st.write(
        "Explore the 26 saved SQL analyses or investigate saved data with a read-only query."
    )
    try:
        settings = apply_preferences(load_settings())
        choice = st.selectbox(
            "Dataset",
            ["Configured dataset", "Saved sample", "Saved provider"],
            key="analytics_dataset",
        )
        if choice != "Configured dataset":
            mode = "sample" if choice == "Saved sample" else "live"
            settings = replace(
                settings,
                data_mode=mode,
                database_url=None,
                read_database_url=None,
                database_path=PROJECT_ROOT / "data/runtime" / f"{mode}.db",
            )
        st.info(
            "SAMPLE DATA · Fictional training records."
            if settings.data_mode == "sample"
            else "SAVED PROVIDER DATA · Results describe imported records, not complete global cricket history."
        )
        st.caption(
            "No API requests are made. Results reflect the last submitted form. Form edits take effect when Run is pressed; switching questions or workspaces clears the result. Each run reads one committed database snapshot."
        )
        database = Database(settings)
        try:
            service = AnalyticsService(database)
            workspace = st.radio(
                "Workspace",
                ["Saved questions", "Custom SQL", "Visualizations"],
                key="analytics_workspace",
                horizontal=True,
            )
            if workspace == "Saved questions":
                _saved(service)
            elif workspace == "Custom SQL":
                _custom(service)
            else:
                render_visualizations(service)
        finally:
            database.close()
    except ConfigurationError:
        st.error("Data settings need attention. Review the setup guide on Home.")
    except (DatabaseError, SQLAlchemyError, OSError):
        st.warning(
            "Saved data or a bundled lesson is unavailable. Review the setup on Home. No automatic creation or repair is attempted."
        )
