"""Shared professional presentation; data and access policies stay in services."""

import streamlit as st


def apply_style():
    """Apply the navy, emerald and white design system to native controls."""
    st.markdown(
        """
        <style>
        :root {--ink:#172b44; --muted:#596b80; --line:#dce4ed; --accent:#087f6b;}
        /* Hide Streamlit hosting actions while keeping the sidebar toggle available. */
        [data-testid="stToolbar"], [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"], #MainMenu {display:none !important;}
        .stApp {background:#f3f6fa; color:var(--ink);}
        .stMainBlockContainer {padding:3.3rem 2.5rem 3rem; max-width:1440px;}
        [data-testid="stVerticalBlock"] {gap:.85rem;}
        h1,h2,h3 {color:var(--ink); letter-spacing:-.035em;}
        h1 {font-size:2.15rem !important; font-weight:750 !important; padding-bottom:.25rem !important;}
        h2 {font-size:1.5rem !important; margin-top:.6rem !important;}
        h3 {font-size:1.12rem !important;}
        p,li {line-height:1.65;}
        [data-testid="stCaptionContainer"] {color:var(--muted); font-size:.82rem;}
        [data-testid="stWidgetLabel"] p {font-weight:600; font-size:.84rem; color:#40546c;}
        [data-testid="stMetric"] {background:#fff; border:1px solid var(--line);
            border-radius:12px; padding:1.1rem 1.25rem; box-shadow:0 3px 12px #172b4405;}
        [data-testid="stMetricLabel"] {color:var(--muted);}
        [data-testid="stMetricValue"] {font-size:2rem; font-weight:700; color:var(--ink);}
        [data-testid="stSidebar"] {background:#10243a; border-right:1px solid #203a54;}
        [data-testid="stSidebar"] * {color:#dce7f3;}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#a6bacf;}
        [data-testid="stSidebar"] h1 {font-size:1.2rem !important; letter-spacing:-.025em; color:#fff;}
        [data-testid="stSidebar"] hr {border-color:#31465d; margin:1.25rem 0;}
        [data-testid="stSidebarNav"] {padding-top:1rem;}
        [data-testid="stSidebarNav"] a {border-radius:8px; margin:.15rem .5rem; padding:.55rem .7rem;}
        [data-testid="stSidebarNav"] a:hover {background:#203b53;}
        [data-testid="stSidebarNav"] a[aria-current="page"] {background:#087f6b; color:#fff;}
        [data-testid="stSidebarNav"] a[aria-current="page"] * {color:#fff; font-weight:650;}
        [data-baseweb="select"] > div, [data-baseweb="input"],
        [data-testid="stNumberInputContainer"], [data-testid="stTextArea"] textarea {
            background:#fff; border-color:#d4dfea; border-radius:8px; color:var(--ink);}
        [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
            border:1px solid #cbd8e4; border-radius:8px; font-weight:600; background:#fff;
            color:#24435c; min-height:2.65rem; transition:background .15s,border-color .15s;}
        [data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background:#eaf6f2; border-color:var(--accent); color:#066653;}
        button[kind="primary"], [data-testid="stFormSubmitButton"] button {
            background:#087f6b; border-color:#087f6b; color:#fff;}
        button:focus-visible, a:focus-visible {outline:3px solid #6ac9b5 !important; outline-offset:3px;}
        [data-testid="stAlert"] {border-radius:9px; border:1px solid #dce6f0; padding:.7rem .95rem;}
        [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div {
            border-color:var(--line); border-radius:12px;}
        [data-testid="stExpander"], [data-testid="stForm"] {background:#fff;}
        [data-testid="stExpander"] details summary {padding:.8rem 1rem;}
        [data-testid="stDataFrame"] {border:1px solid var(--line); border-radius:10px; overflow:hidden;}
        [data-baseweb="tab-list"] {gap:1.25rem; border-bottom:1px solid var(--line);}
        [data-baseweb="tab"] {font-weight:600; padding:.65rem .1rem;}
        [data-testid="stCode"] {border:1px solid var(--line); border-radius:10px;}
        hr {border-color:var(--line);}
        @media (max-width:700px) {
            .stMainBlockContainer {padding:3.5rem 1rem 2rem;}
            h1 {font-size:1.75rem !important;}
            [data-testid="stMetric"] {padding:.8rem;}
        }
        @media (prefers-reduced-motion:reduce) {* {transition:none !important;}}
        </style>
        """,
        unsafe_allow_html=True,
    )
