"""Live Matches route."""

from ui.errors import page_error_boundary
from ui.live_matches import render_live_matches

with page_error_boundary("Live Matches"):
    render_live_matches()
