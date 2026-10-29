"""Streamlit entry point and explicit navigation for implemented pages."""

import streamlit as st

from ui.errors import page_error_boundary


def main():
    """Register completed pages only; opening Home never starts an API client."""
    st.set_page_config(
        page_title="Cricbuzz LiveStats",
        page_icon="🏏",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    from ui.style import apply_style

    apply_style()
    with st.sidebar:
        st.title("🏏 Cricbuzz LiveStats")
        st.caption("Cricket insights & SQL analytics")
    page = st.navigation(
        [
            st.Page("pages/01_Home.py", title="Home", icon="🏠", default=True),
            st.Page("pages/02_Live_Matches.py", title="Live Matches", icon="🏏"),
            st.Page("pages/03_Top_Players.py", title="Top Players", icon="⭐"),
            st.Page("pages/04_Analytics.py", title="Analytics", icon="📊"),
            st.Page("pages/05_CRUD.py", title="CRUD", icon="✏️"),
            st.Page("pages/06_Settings.py", title="Settings", icon="⚙️"),
        ]
    )
    with st.sidebar:
        st.divider()
        st.caption("SAVED CRICKET INSIGHTS")
        st.write("Matches · Players · Analytics")
        st.caption("Check the dataset label and import time for coverage.")
    with page_error_boundary("application"):
        page.run()


if __name__ == "__main__":
    main()
