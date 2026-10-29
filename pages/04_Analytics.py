"""Analytics route."""

from ui.analytics import render_analytics
from ui.errors import page_error_boundary

with page_error_boundary("Analytics"):
    render_analytics()
