"""Live Matches page: saved snapshots first, explicit provider actions only."""

from dataclasses import replace

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from api.client import APIError
from config import PROJECT_ROOT, ConfigurationError, load_settings
from services.live_matches import LiveMatchService, RefreshCoordinator
from ui.preferences import apply_preferences
from utils.cricket import balls_to_overs
from utils.dates import display_timestamp
from utils.db_connection import Database, DatabaseError
from utils.logging_config import log_event


@st.cache_resource
def refresh_coordinator():
    """Share cooldown/lock across reruns and sessions in this one app process."""
    return RefreshCoordinator()


def shown(value):
    """Display unknown statistics explicitly instead of converting them into zero."""
    return "Unknown" if value is None else str(value)


def time_label(value, timezone):
    """Format a saved timestamp safely in the chosen display timezone."""
    if not value:
        return "Not available"
    try:
        return display_timestamp(value, timezone)
    except ValueError:
        return "Not available"


def refresh(database, match_id=None):
    """Handle one button action without exposing response bodies or credentials."""
    try:
        with st.spinner("Fetching and validating provider data…"):
            result = refresh_coordinator().refresh(database, match_id)
        if result["status"] == "stale":
            st.warning(
                "The provider snapshot was older than saved data; saved data was kept."
            )
        else:
            st.success(
                "Provider request completed. The saved view below has been reloaded."
            )
        if match_id is None:
            st.caption(
                f"This response contained {result['match_count']} matches. Older saved records are retained and may no longer be ongoing."
            )
    except APIError as error:
        log_event("api_refresh", error.code, "Live Matches")
        messages = {
            "configuration": "API or database settings need attention. Review the setup guide on Home.",
            "cooldown": "Please wait before another refresh. Refreshes share a minimum 30-second cooldown.",
            "authentication": "The provider rejected authentication. Check the private API settings.",
            "rate_limit": "The provider request limit was reached. Wait before trying again.",
            "timeout": "The provider did not respond in time.",
            "network": "The provider could not be reached.",
        }
        st.warning(
            messages.get(error.code, "The provider response could not be imported.")
        )
        st.caption("Saved data has been kept. No successful refresh is claimed.")
    except (DatabaseError, SQLAlchemyError, OSError, ValueError):
        st.warning(
            "The refresh could not be completed. Review the local setup; saved data remains available."
        )


def _innings(innings, timezone):
    """Render saved innings summaries and batting/bowling tables with coverage labels."""
    if not innings:
        st.info("No innings or detailed scorecard has been saved for this match yet.")
        return
    for inning in innings:
        with st.expander(
            f"Innings {inning['innings_number']} · {inning['batting_team']}",
            expanded=True,
        ):
            if inning["is_super_over"]:
                st.caption("Super over · separate from ordinary innings statistics")
            overs = (
                balls_to_overs(inning["legal_balls"])
                if inning["legal_balls"] is not None
                else "Unknown"
            )
            st.write(
                f"{shown(inning['total_runs'])}/{shown(inning['wickets'])} · {overs} overs"
            )
            st.caption(
                f"Innings summary imported: {time_label(inning['fetched_at'], timezone)} · Coverage: {shown(inning['completeness'])}"
            )
            tabs = st.tabs(["Batting", "Bowling"])
            for tab, kind in zip(tabs, ("batting", "bowling"), strict=True):
                with tab:
                    rows = []
                    for item in inning[kind]:
                        item = dict(item)
                        if kind == "batting":
                            item["Strike rate"] = (
                                round(100 * item["runs"] / item["balls_faced"], 2)
                                if item["runs"] is not None and item["balls_faced"]
                                else None
                            )
                        else:
                            balls = item.pop("legal_balls")
                            item["Overs"] = (
                                balls_to_overs(balls) if balls is not None else None
                            )
                            item["Economy"] = (
                                round(6 * item["runs_conceded"] / balls, 2)
                                if item["runs_conceded"] is not None and balls
                                else None
                            )
                        item["imported_at"] = time_label(item["imported_at"], timezone)
                        rows.append(item)
                    if rows:
                        labels = {
                            "player": "Player",
                            "batting_position": "Position",
                            "runs": "Runs",
                            "balls_faced": "Balls",
                            "fours": "4s",
                            "sixes": "6s",
                            "dismissal_text": "Dismissal",
                            "is_dismissed": "Dismissed",
                            "ownership": "Record source",
                            "imported_at": "Imported at",
                            "maidens": "Maidens",
                            "runs_conceded": "Runs conceded",
                            "wickets": "Wickets",
                        }
                        st.dataframe(
                            pd.DataFrame(rows).rename(columns=labels),
                            hide_index=True,
                            width="stretch",
                        )
                    else:
                        st.info(f"No detailed {kind} records saved for this innings.")


def _page(database):
    """Render the selected dataset through services while respecting its access policy."""
    settings = database.settings
    sample = settings.data_mode == "sample"
    st.info(
        "SAMPLE DATA · Fictional training scorecards."
        if sample
        else "SAVED PROVIDER DATA · These snapshots may be out of date. Use an explicit refresh for a new provider response."
    )
    st.caption(
        "Changing filters or matches only reads saved data. Missing statistics stay unknown; individual rows may have different import times."
    )
    allowed = not sample and settings.access_mode == "local"
    if st.button(
        "Refresh match list from API",
        disabled=not allowed,
        key="refresh_live_list",
        help="Uses provider quota. Requires a writable live dataset and configured private API access.",
    ):
        refresh(database)
    if not allowed:
        st.caption("API refresh is disabled for sample and read-only datasets.")
    service = LiveMatchService(database)
    matches = service.matches()
    status = st.selectbox(
        "Match status",
        [
            "Ongoing in saved data",
            "All saved matches",
            "Completed",
            "Scheduled",
            "Abandoned",
            "Unknown",
        ],
        index=1 if sample else 0,
        key="live_status",
    )
    statuses = {
        "Ongoing in saved data": "live",
        "Completed": "completed",
        "Scheduled": "scheduled",
        "Abandoned": "abandoned",
        "Unknown": "unknown",
    }
    filtered = (
        matches
        if status == "All saved matches"
        else [m for m in matches if m["status"] == statuses[status]]
    )
    st.caption(
        f"{len(filtered)} matching saved matches · {len(matches)} total stored matches"
    )
    if not filtered:
        st.info(
            "No matches match this saved-data filter. Try All saved matches or refresh the provider list in a writable live dataset."
        )
        return
    by_id = {m["match_id"]: m for m in filtered}
    selected = st.selectbox(
        "Choose a match",
        list(by_id),
        format_func=lambda mid: (
            f"{by_id[mid]['team1'] or 'Unknown team'} vs {by_id[mid]['team2'] or 'Unknown team'} · {by_id[mid]['description']} · #{mid}"
        ),
        key="selected_live_match",
    )
    match = by_id[selected]
    st.subheader(
        f"{match['team1'] or 'Unknown team'} vs {match['team2'] or 'Unknown team'}"
    )
    st.write(match["status_text"] or "Match status details unavailable")
    st.caption(
        f"{match['format']} · {match['description']} · Saved status: {match['status']}"
    )
    st.write(
        f"Venue: {match['venue'] or 'Unknown'} · {match['city'] or 'Unknown city'}"
    )
    st.caption(f"Starts: {time_label(match['starts_at'], settings.display_timezone)}")
    st.caption(
        f"Source: {match['source'] or 'Unknown'} · Match imported: {time_label(match['fetched_at'], settings.display_timezone)} · Coverage: {match['completeness'] or 'Unknown'}"
    )
    if st.button(
        "Refresh selected scorecard from API",
        disabled=not allowed
        or match["source"] != "cricketapilive-cricbuzz-cricket/v2/provider",
        key="refresh_live_scorecard",
        help="Uses provider quota for the selected match only.",
    ):
        refresh(database, selected)
    _innings(service.scorecard(selected), settings.display_timezone)


def render_live_matches():
    """Render saved matches and explicit guarded scorecard/list refresh controls."""
    st.caption("CRICBUZZ LIVESTATS / MATCH CENTRE")
    st.title("Live Matches")
    st.write("Explore saved match snapshots and detailed innings scorecards.")
    try:
        configured = apply_preferences(load_settings())
        choice = st.selectbox(
            "Dataset",
            ["Configured dataset", "Saved sample", "Saved provider"],
            key="live_dataset",
        )
        if choice != "Configured dataset":
            mode = "sample" if choice == "Saved sample" else "live"
            configured = replace(
                configured,
                data_mode=mode,
                database_url=None,
                read_database_url=None,
                database_path=PROJECT_ROOT / "data/runtime" / f"{mode}.db",
            )
        database = Database(configured)
        try:
            _page(database)
        finally:
            database.close()
    except ConfigurationError:
        st.error("Data settings need attention. Review the setup guide on Home.")
    except (DatabaseError, SQLAlchemyError, OSError):
        st.warning(
            "The selected saved database is unavailable or incompatible. Review the setup guide on Home. No automatic database creation or repair is attempted."
        )
