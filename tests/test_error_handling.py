"""Safe diagnostics and route recovery preserve control flow and saved records."""

import io
import logging
from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError
from streamlit.errors import StreamlitAPIException
from streamlit.runtime.scriptrunner_utils.exceptions import StopException
from streamlit.testing.v1 import AppTest

from api.client import APIError, CricbuzzClient, ProviderContract
from config import PROJECT_ROOT, ConfigurationError
from database.repositories import StaleRecordError
from ui.errors import error_code, page_error_boundary
from utils.db_connection import DatabaseError
from utils.logging_config import log_event


@pytest.mark.parametrize(
    "error,code",
    [
        (ConfigurationError("private"), "configuration"),
        (StaleRecordError("private"), "stale_record"),
        (DatabaseError("private"), "database"),
        (OperationalError("private", {}, Exception("secret")), "database"),
        (APIError("json", "secret"), "json"),
        (ValueError("private"), "validation"),
        (RuntimeError("private"), "unexpected"),
    ],
)
def test_classification_never_uses_raw_error_text(error, code):
    assert error_code(error) == code


def test_logs_allow_only_fixed_vocabulary_and_no_traceback():
    logger = logging.getLogger("cricbuzz.safe_events")
    original = logger.handlers[:]
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger.handlers = [handler]
    try:
        log_event("api_refresh", "authentication", "Live Matches")
        log_event("secret-key", "https://secret.example", "private-file")
        value = stream.getvalue()
        assert "code=authentication" in value
        assert "secret" not in value and "private-file" not in value
        assert "Traceback" not in value
    finally:
        logger.handlers = original


@pytest.mark.parametrize("error", [StopException(), KeyboardInterrupt(), SystemExit()])
def test_control_flow_and_process_interrupts_are_not_swallowed(error):
    with pytest.raises(type(error)):
        with page_error_boundary("Home"):
            raise error


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("private-marker"),
        StreamlitAPIException("private-marker"),
        ValueError("private-marker"),
    ],
)
def test_route_boundary_shows_recovery_without_error_details(
    settings, monkeypatch, error
):
    def fail():
        raise error

    monkeypatch.setattr("ui.home.render_home", fail)
    at = AppTest.from_file(
        str(PROJECT_ROOT / "pages/01_Home.py"), default_timeout=15
    ).run()
    assert not at.exception and at.error
    assert "private-marker" not in str(
        [x.value for x in at.error] + [x.value for x in at.caption]
    )
    assert any("may already have committed" in x.value for x in at.caption)


def test_page_recovers_after_transient_unexpected_failure(settings, monkeypatch):
    import ui.home

    render = ui.home.render_home
    monkeypatch.setattr("ui.home.load_settings", lambda: settings)
    monkeypatch.setattr(
        "ui.home.render_home", lambda: (_ for _ in ()).throw(RuntimeError("sensitive"))
    )
    at = AppTest.from_file(str(PROJECT_ROOT / "main.py"), default_timeout=15).run()
    assert at.error
    monkeypatch.setattr("ui.home.render_home", render)
    at.run()
    assert not at.exception and not at.error and at.metric


def test_client_clears_key_even_if_session_cleanup_fails():
    class Session:
        def close(self):
            raise RuntimeError("cleanup failure")

    contract = ProviderContract(
        "fixture", "v1", "https://fixture.example", "X-Key", {}, verified=True
    )
    client = CricbuzzClient(contract, "placeholder", session=Session())
    with pytest.raises(RuntimeError):
        client.close()
    assert client._key == ""


def test_page_boundary_does_not_commit_a_failed_write(database):
    before = None
    with database.transaction() as c:
        before = c.exec_driver_sql(
            "SELECT full_name FROM players WHERE player_id=1"
        ).scalar_one()
    with patch("ui.errors.st.error"), patch("ui.errors.st.caption"):
        with page_error_boundary("CRUD"):
            with database.transaction(write=True) as c:
                c.exec_driver_sql(
                    "UPDATE players SET full_name='temporary' WHERE player_id=1"
                )
                raise RuntimeError("sensitive")
    with database.transaction() as c:
        assert (
            c.exec_driver_sql(
                "SELECT full_name FROM players WHERE player_id=1"
            ).scalar_one()
            == before
        )
        assert c.exec_driver_sql("SELECT revision FROM dataset_state").scalar_one() == 1


def test_unavailable_console_does_not_break_error_recovery():
    from utils.logging_config import _SafeConsoleHandler

    class ClosedConsole:
        def write(self, value):
            raise OSError("unavailable")

    record = logging.LogRecord(
        "cricbuzz.safe_events",
        logging.WARNING,
        "",
        0,
        "event=page_render code=unexpected scope=Home",
        (),
        None,
    )
    with patch("utils.logging_config.sys.stderr", ClosedConsole()):
        _SafeConsoleHandler().emit(record)
