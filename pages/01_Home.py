"""Home route; reusable presentation lives outside the navigation script."""

from ui.errors import page_error_boundary
from ui.home import render_home

with page_error_boundary("Home"):
    render_home()
