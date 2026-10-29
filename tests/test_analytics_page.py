"""All saved lessons plus adversarial custom SQL and real Streamlit controls."""

from dataclasses import replace
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from config import PROJECT_ROOT
from services.analytics import (
    QUESTIONS,
    AnalyticsError,
    AnalyticsService,
    parameters,
    saved_sql,
)

SOURCE = "Synthetic training fixture"


@pytest.mark.parametrize("query_id", [q.id for q in QUESTIONS])
def test_every_saved_question_runs_under_restricted_reader(database, query_id):
    result = AnalyticsService(database).run_saved(query_id, "2026-10-01", SOURCE)
    assert result["columns"] and isinstance(result["rows"], list)
    assert result["revision"] == 1


def test_venue_variant_and_calendar_parameters(database):
    result = AnalyticsService(database).run_saved(
        "Q22", "2026-10-01", venue_breakdown=True
    )
    assert len(result["rows"]) == 8
    assert parameters("Q22", "2024-02-29")["window_start"] == "2021-02-28T00:00:00Z"
    assert parameters("Q25", "2026-10-28") == {
        "window_start": "2023-10-01T00:00:00Z",
        "window_end": "2026-10-01T00:00:00Z",
    }
    assert parameters("Q02", "2026-10-01")["window_start"] == "2026-09-01T00:00:00Z"
    with pytest.raises(AnalyticsError):
        saved_sql("../.env")
    with pytest.raises(AnalyticsError):
        parameters("Q01", "not a date")
    with pytest.raises(AnalyticsError):
        parameters("Q03", "2026-10-01")


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM players",
        "UPDATE players SET full_name='changed'",
        "DROP TABLE players",
        "ATTACH DATABASE ':memory:' AS other",
        "PRAGMA query_only=OFF",
        "SELECT load_extension('anything')",
        "SELECT readfile('/etc/passwd')",
        "BEGIN",
        "SELECT 1; SELECT 2",
        "CREATE TEMP TABLE scratch(x)",
        "WITH x AS (SELECT 1) DELETE FROM players",
    ],
)
def test_custom_sql_cannot_write_or_escape_reader(database, sql):
    service = AnalyticsService(database)
    with pytest.raises(AnalyticsError):
        service.run_custom(sql)
    assert service.run_custom("SELECT COUNT(*) FROM players")["rows"] == [[12]]
    assert service.run_custom("SELECT revision FROM dataset_state")["rows"] == [[1]]


def test_custom_cte_window_and_duplicate_columns_allowed(database):
    result = AnalyticsService(database).run_custom(
        "WITH x AS (SELECT 2 AS n UNION ALL SELECT 1) SELECT n AS same, ROW_NUMBER() OVER(ORDER BY n) AS same FROM x ORDER BY n"
    )
    assert result["columns"] == ["same", "same"]
    assert result["rows"] == [[1, 1], [2, 2]]


def test_row_cap_and_oversized_values(database):
    service = AnalyticsService(database)
    result = service.run_custom("SELECT * FROM matches", row_limit=5)
    assert len(result["rows"]) == 5 and result["truncated"]
    with pytest.raises(AnalyticsError):
        service.run_custom("SELECT '" + "a" * 21000 + "'")
    with pytest.raises(AnalyticsError):
        service.run_custom("SELECT 1", row_limit=True)
    assert service.run_custom("SELECT printf('%99999999s','a')")["rows"] == [[None]]
    bounded = service.run_custom(
        "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<10) SELECT printf('%150000s','a') FROM n"
    )
    assert bounded["truncated"] and len(bounded["rows"]) == 6


def test_recursive_query_interrupts_and_connection_remains_usable(database):
    service = AnalyticsService(database)
    with pytest.raises(AnalyticsError):
        service._read(
            "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n) SELECT SUM(x) FROM n",
            {},
            seconds=0.01,
        )
    assert service.run_custom("SELECT 42")["rows"] == [[42]]


def test_public_readonly_denies_custom_but_allows_saved(database):
    database.settings = replace(database.settings, access_mode="public_readonly")
    service = AnalyticsService(database)
    with pytest.raises(AnalyticsError):
        service.run_custom("SELECT 1")
    assert service.run_saved("Q05", "2026-10-01")["rows"]


def page(settings, monkeypatch):
    monkeypatch.setattr("ui.analytics.load_settings", lambda: settings)
    return AppTest.from_file(
        str(PROJECT_ROOT / "pages/04_Analytics.py"), default_timeout=15
    ).run()


def test_ui_saved_submission_and_question_change_clears_results(settings, monkeypatch):
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("No API")
    ) as network:
        at = page(settings, monkeypatch)
        assert not at.exception and not at.dataframe
        assert len(at.selectbox(key="analytics_question").options) == 26
        at.button(key="FormSubmitter:saved_analytics-Run saved question").click().run()
        assert not at.exception and at.dataframe
        at.selectbox(key="analytics_question").select("Q05").run()
        assert not at.dataframe and not at.exception
        assert not network.called


def test_ui_custom_errors_and_readonly_gate(settings, monkeypatch):
    at = page(settings, monkeypatch)
    at.radio(key="analytics_workspace").set_value("Custom SQL").run()
    at.text_area(key="custom_sql").set_value("DELETE FROM players")
    at.button(key="FormSubmitter:custom_analytics-Run custom query").click().run()
    assert not at.exception and at.warning
    at = page(replace(settings, access_mode="public_readonly"), monkeypatch)
    at.radio(key="analytics_workspace").set_value("Custom SQL").run()
    assert not at.text_area and not at.exception


def test_missing_database_is_not_created(settings, monkeypatch, tmp_path):
    target = tmp_path / "missing.db"
    at = page(replace(settings, database_path=target), monkeypatch)
    at.button(key="FormSubmitter:saved_analytics-Run saved question").click().run()
    assert at.warning and not at.exception and not target.exists()


def test_coverage_summary_preserves_match_grain(database):
    result = AnalyticsService(database).run_saved("Q26", "2026-10-01")
    rows = [dict(zip(result["columns"], r, strict=True)) for r in result["rows"]]
    assert sum(r["saved_matches"] for r in rows) == 72
    assert sum(r["saved_innings"] for r in rows) == 192
    assert sum(r["matches_with_innings"] for r in rows) == 72
    assert {r["saved_status"] for r in rows} == {"completed"}
    assert {r["source_name"] for r in rows} == {"Synthetic training fixture"}
