"""Last-resort page recovery without swallowing Streamlit control flow."""

from contextlib import contextmanager

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from api.client import APIError
from config import ConfigurationError
from database.repositories import StaleRecordError
from utils.db_connection import DatabaseError
from utils.logging_config import SCOPES, log_event


def error_code(error):
    """Map expected failure types to allowlisted diagnostics without private details."""
    if isinstance(error, ConfigurationError):
        return "configuration"
    if isinstance(error, StaleRecordError):
        return "stale_record"
    if isinstance(error, (DatabaseError, SQLAlchemyError)):
        return "database"
    if isinstance(error, APIError):
        return error.code
    if isinstance(error, ValueError):
        return "validation"
    return "unexpected"


@contextmanager
def page_error_boundary(scope):
    """Catch ordinary failures at the route; rerun/stop/interrupt still propagate."""
    try:
        yield
    except Exception as error:
        scope = scope if scope in SCOPES else "application"
        log_event("page_render", error_code(error), scope)
        st.error(
            "This page could not finish loading. No private error details are displayed."
        )
        st.caption(
            "Reload the page or open Home to review setup. Before repeating an edit or refresh, inspect saved records: an operation may already have committed before this display error."
        )
