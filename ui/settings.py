"""Settings diagnostics and safe session-only display controls."""

from dataclasses import replace
from datetime import UTC, datetime

import streamlit as st

from config import PROJECT_ROOT, ConfigurationError, load_settings
from services.settings_status import api_readiness, database_health
from ui.preferences import apply_preferences
from utils.dates import display_timestamp

TIMEZONES = [
    "Asia/Kolkata",
    "UTC",
    "Europe/London",
    "Australia/Sydney",
    "Africa/Johannesburg",
    "America/New_York",
]


def render_settings():
    """Display safe local health and session preferences without revealing credentials."""
    st.caption("CRICBUZZ LIVESTATS / SETTINGS")
    st.title("Settings")
    st.write("Review local data health and adjust how timestamps are displayed.")
    st.caption(
        "No API request, database write or private-file edit is performed on this page."
    )
    st.button("Recheck local status", key="settings_recheck")
    try:
        configured = load_settings()
    except ConfigurationError:
        st.error(
            "Application configuration needs attention. Review the setup guide on Home. Private settings are not displayed here."
        )
        configured = None
    if configured:
        effective = apply_preferences(configured)
        st.subheader("Display preferences")
        options = list(dict.fromkeys([configured.display_timezone, *TIMEZONES]))
        with st.form("settings_display"):
            timezone = st.selectbox(
                "Display timezone",
                options,
                index=options.index(effective.display_timezone)
                if effective.display_timezone in options
                else 0,
                key="settings_timezone",
            )
            apply = st.form_submit_button("Apply for this session")
            reset = st.form_submit_button("Reset to configured timezone")
        if apply or reset:
            if reset:
                st.session_state.pop("display_timezone_override", None)
            else:
                st.session_state["display_timezone_override"] = timezone
            effective = apply_preferences(configured)
            st.success(
                f"Display timezone: {effective.display_timezone}. Other pages use this preference on their next rerun."
            )
        st.caption(
            f"Configured timezone: {configured.display_timezone} · Effective timezone: {effective.display_timezone}. This preference lasts for this browser session and does not edit .env."
        )
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        st.write(
            "Current time preview: "
            + display_timestamp(now, effective.display_timezone)
        )
        st.subheader("Database status")
        choice = st.selectbox(
            "Database to inspect",
            ["Configured database", "Saved sample", "Saved provider"],
            key="settings_database",
        )
        target = configured
        if choice != "Configured database":
            mode = "sample" if choice == "Saved sample" else "live"
            target = replace(
                configured,
                data_mode=mode,
                database_url=None,
                read_database_url=None,
                database_path=PROJECT_ROOT / "data/runtime" / f"{mode}.db",
            )
        health = database_health(target)
        if health["available"]:
            st.success(
                "Database is readable and its schema and dataset mode are supported."
            )
            st.write(
                f"Dataset: {health['mode']} · Schema version: {health['schema_version']} · Revision: {health['revision']}"
            )
            st.caption(
                f"Saved matches: {health['matches']} · Active players: {health['players']} · Teams: {health['teams']} · Venues: {health['venues']}"
            )
            if target.data_mode == "sample":
                st.info(
                    "Sample records are fictional. Schema 1 sample reads are supported; live API refresh requires schema 2."
                )
        else:
            st.warning(
                "This target is absent, unreadable or incompatible with the selected mode. Follow the setup guide; no initialization or migration was attempted."
            )
        st.subheader("Access policy")
        st.write(
            "Local operator"
            if configured.access_mode == "local"
            else "Public read-only"
        )
        st.caption(
            "Access policy comes from trusted deployment configuration and cannot be changed here. Local mode enables administrative forms and restricted custom SQL; public read-only mode disables them and provider refresh writes."
        )
    if configured and configured.access_mode == "public_readonly":
        st.subheader("Data updates")
        st.info(
            "Provider records are refreshed by a scheduled backend job. Check import times for freshness; this is not continuous live scoring."
            if configured.data_mode == "live"
            else "Sample demo—live API access is disabled."
        )
        st.caption(
            "Administrative edits and visitor-triggered API requests are disabled."
        )
        return
    st.subheader("API configuration readiness")
    api = api_readiness()
    if api["configured"]:
        st.success("Private key and a valid reviewed provider contract are configured.")
        st.write(f"Provider: {api['provider']} · Version: {api['version']}")
        st.caption(
            "Credential value is hidden. Configuration readiness does not verify the key, subscription, remaining quota, provider availability or current scores."
        )
        with st.expander("Refresh policy"):
            st.write(
                f"Connect timeout: {api['connect_timeout']} seconds · Read timeout: {api['read_timeout']} seconds"
            )
            st.write(
                f"Maximum attempts: {api['max_attempts']} · Operation budget: {api['operation_budget']} seconds"
            )
            st.write(f"Contract minimum interval: {api['minimum_interval']} seconds")
            st.caption(
                "Live Matches adds a shared minimum 30-second cooldown, extended by a longer contract interval or Retry-After. It is process-local and resets on restart; no automatic polling is enabled."
            )
    else:
        st.info(
            "API configuration is incomplete or invalid. Sample browsing and SQL lessons do not require API access. Configure the key privately using the API setup guide on Home."
        )
    st.subheader("Setup and privacy")
    st.markdown(
        "Use the bundled guides on **Home** for database setup, API configuration and project folders. Keep credentials in the private configuration file. This page never displays key fragments, raw connection URLs or private-file contents."
    )
    st.caption(
        "Charts are available in Top Players and Analytics. Saved provider history remains limited."
    )
