"""Session-only display preferences; never override access or database settings."""

from dataclasses import replace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import streamlit as st


def apply_preferences(settings):
    """Apply a validated session timezone without changing persisted configuration."""
    timezone = st.session_state.get("display_timezone_override")
    if timezone is None:
        return settings
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return settings
    return replace(settings, display_timezone=timezone)
