"""CRUD route."""

from ui.crud import render_crud
from ui.errors import page_error_boundary

with page_error_boundary("CRUD"):
    render_crud()
