"""Top Players route."""

from ui.errors import page_error_boundary
from ui.top_players import render_top_players

with page_error_boundary("Top Players"):
    render_top_players()
