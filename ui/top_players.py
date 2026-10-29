"""Top Players: honest stored-career rankings and inspectable profiles."""

from dataclasses import replace

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import PROJECT_ROOT, ConfigurationError, load_settings
from services.player_stats import PlayerStatsService
from services.top_players import METRICS, TopPlayersService
from ui.live_matches import time_label
from ui.preferences import apply_preferences
from ui.visualizations import leaderboard_charts
from utils.db_connection import Database, DatabaseError

LABELS = {
    "rank": "Rank",
    "player_name": "Player",
    "matches_played": "Matches",
    "runs": "Runs",
    "highest_score": "Highest score",
    "centuries": "Centuries",
    "wickets": "Wickets",
    "batting_average": "Batting average",
    "strike_rate": "Strike rate",
    "bowling_average": "Bowling average",
    "economy": "Economy",
    "fetched_at": "Imported at",
    "completeness": "Coverage",
}


def _page(database):
    """Render the selected dataset through services while respecting its access policy."""
    settings = database.settings
    sample = settings.data_mode == "sample"
    st.info(
        "SAMPLE DATA · Fictional career statistics."
        if sample
        else "SAVED PROVIDER DATA · Rankings cover only imported players, not all cricket players worldwide."
    )
    st.caption(
        "Opening this page and changing filters make no API requests. Career snapshots are not summed. Charts describe only these saved records."
    )
    st.button(
        "Reload saved statistics",
        key="reload_top_players",
        help="Reread local career statistics without spending API quota.",
    )
    service = TopPlayersService(database)
    catalog = service.catalog()
    if not catalog:
        st.info(
            "No career statistics are saved in this dataset yet. Match scorecards alone do not establish career totals. See the API setup guide on Home to import player careers."
        )
        return
    sources = {r["source_id"]: r["source_name"] for r in catalog}
    filters = st.columns(3)
    with filters[0]:
        source = st.selectbox(
            "Statistics source",
            list(sources),
            format_func=sources.get,
            key="top_source",
        )
    formats = {
        r["format_id"]: r["format_code"] for r in catalog if r["source_id"] == source
    }
    with filters[1]:
        fmt = st.selectbox(
            "Cricket format", list(formats), format_func=formats.get, key="top_format"
        )
    st.caption(f"Source: {sources[source]} · Exact stored format: {formats[fmt]}")
    if formats[fmt] == "INTERNATIONAL_T20":
        st.caption(
            "INTERNATIONAL_T20 is the provider's stored category; it has not been relabeled as official T20I."
        )
    with filters[2]:
        metric = st.selectbox("Rank by", list(METRICS), key="top_metric")
    columns = st.columns(2)
    with columns[0]:
        limit = st.selectbox("Players to display", [10, 20, 50, 100], key="top_limit")
    with columns[1]:
        minimum = st.number_input(
            "Minimum career matches",
            min_value=0,
            max_value=100000,
            value=0,
            step=1,
            key="top_minimum",
        )
    with st.expander("How qualification works"):
        st.caption(
            "Minimum 0 applies no match-count filter, including players with an unknown match count. Positive minimums require a known count. No dismissals or wicket minimum is applied to rate rankings; inspect sample size before comparing."
        )
    result = service.leaders(source, fmt, metric, limit=limit, minimum_matches=minimum)
    coverage = result["coverage"]
    cols = st.columns(3)
    for col, label, value in zip(
        cols,
        ["Players after match filter", "Known ranking values", "Displayed players"],
        [coverage["eligible_players"], coverage["ranked_players"], len(result["rows"])],
        strict=True,
    ):
        col.metric(label, value)
    st.caption(
        f"Import range after match filter: {time_label(coverage['oldest_import'], settings.display_timezone)} to {time_label(coverage['newest_import'], settings.display_timezone)}. Different players may have different snapshot dates."
    )
    if coverage["eligible_players"] < 10:
        st.warning(
            "Limited player coverage: this saved dataset is too small to represent a global leaderboard."
        )
    rows = result["rows"]
    if not rows:
        st.info(
            "No known values qualify for this ranking and match filter. Unknown statistics are not replaced by zero."
        )
        return
    order = "Lower is better" if METRICS[metric][1] == "ASC" else "Higher is better"
    st.subheader(metric)
    st.caption(
        f"{order} · Equal unrounded values share a rank. The display limit caps rows, so a tie group can be truncated. Player IDs stabilize display order."
    )
    leaderboard_charts(
        rows,
        metric,
        f"{settings.data_mode.upper()} · {sources[source]} · {formats[fmt]}",
    )
    table = []
    for row in rows:
        record = {k: row[k] for k in LABELS}
        record["fetched_at"] = time_label(
            record["fetched_at"], settings.display_timezone
        )
        for field in ("batting_average", "strike_rate", "bowling_average", "economy"):
            if record[field] is not None:
                record[field] = round(record[field], 2)
        table.append(record)
    st.dataframe(
        pd.DataFrame(table).rename(columns=LABELS), hide_index=True, width="stretch"
    )
    with st.expander("How missing statistics are handled"):
        st.caption(
            "Blank cells mean unknown or undefined. Known zero totals remain zero. Ratios are calculated from known positive denominators; reported ratios are used only when the denominator is missing. A known zero denominator stays undefined."
        )
    selected = st.selectbox(
        "Inspect a displayed player",
        [r["player_id"] for r in rows],
        format_func=lambda pid: next(
            f"{r['player_name']} · #{pid}" for r in rows if r["player_id"] == pid
        ),
        key="top_player",
    )
    profile = PlayerStatsService(database).profile(selected)
    with st.expander("Player profile and career scope", expanded=False):
        if profile is None:
            st.info(
                "This player changed or is no longer active. Reload saved statistics."
            )
        else:
            st.write(profile["full_name"])
            for label, key in [
                ("Role", "role"),
                ("Batting style", "batting_style"),
                ("Bowling style", "bowling_style"),
            ]:
                st.write(f"{label}: {profile[key] or 'Unknown'}")
            row = next(r for r in rows if r["player_id"] == selected)
            st.caption(
                f"Career snapshot: {formats[fmt]} · {sources[source]} · Imported {time_label(row['fetched_at'], settings.display_timezone)} · Coverage: {row['completeness']}"
            )
            st.caption(
                "This is the selected format's latest committed career snapshot. Limited match-level history is not used to reconstruct missing career statistics."
            )


def render_top_players():
    """Render exact-source/format career rankings from the selected saved dataset."""
    st.caption("CRICBUZZ LIVESTATS / PLAYER STATISTICS")
    st.title("Top Players")
    st.write("Compare saved career totals and rates, one source and format at a time.")
    try:
        settings = apply_preferences(load_settings())
        choice = st.selectbox(
            "Dataset",
            ["Configured dataset", "Saved sample", "Saved provider"],
            key="top_dataset",
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
        database = Database(settings)
        try:
            _page(database)
        finally:
            database.close()
    except ConfigurationError:
        st.error("Data settings need attention. Review the setup guide on Home.")
    except (DatabaseError, SQLAlchemyError, OSError):
        st.warning(
            "The selected saved database is unavailable or incompatible. Review the setup guide on Home. No automatic setup or repair is attempted."
        )
