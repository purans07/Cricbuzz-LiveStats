"""Settings route."""

from ui.errors import page_error_boundary
from ui.settings import render_settings

with page_error_boundary("Settings"):
    render_settings()
