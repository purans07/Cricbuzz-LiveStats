"""Allowlisted diagnostic events; never log raw errors, SQL, URLs or credentials."""

import logging
import sys
from threading import Lock

EVENTS = {"page_render", "api_refresh", "crud_write", "client_cleanup"}
CODES = {
    "configuration",
    "database",
    "authentication",
    "rate_limit",
    "network",
    "timeout",
    "json",
    "shape",
    "size",
    "normalization",
    "provenance",
    "mock",
    "input",
    "cooldown",
    "upstream",
    "http",
    "tls",
    "not_found",
    "validation",
    "stale_record",
    "unexpected",
    "cleanup",
}
SCOPES = {
    "Home",
    "Live Matches",
    "Top Players",
    "Analytics",
    "CRUD",
    "Settings",
    "application",
}


_SETUP_LOCK = Lock()


class _SafeConsoleHandler(logging.Handler):
    """Use current stderr and keep a closed console from breaking recovery."""

    def emit(self, record):
        """Emit only the approved diagnostic fields through the dedicated safe logger."""
        try:
            sys.stderr.write(self.format(record) + "\n")
        except (OSError, ValueError):
            pass


def log_event(event, code, scope="application"):
    """Use fixed vocabulary only, including for unrecognized caller-supplied codes."""
    logger = logging.getLogger("cricbuzz.safe_events")
    with _SETUP_LOCK:
        if not logger.handlers:
            handler = _SafeConsoleHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
            logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    event = event if event in EVENTS else "page_render"
    code = code if code in CODES else "unexpected"
    scope = scope if scope in SCOPES else "application"
    logger.warning("event=%s code=%s scope=%s", event, code, scope)
