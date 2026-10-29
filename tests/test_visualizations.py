"""Chart grain, gaps, unknown values, scope and real UI execution."""

from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from config import PROJECT_ROOT
from utils.charts import (
    consistency_scatter,
    player_comparison,
    quarterly_heatmap,
    quarterly_line,
    ranking_bar,
    venue_bar,
)


def career(pid, value):
    return {
        "player_id": pid,
        "player_name": "Same name",
        "ranking_value": value,
        "rank": 1,
        "matches_played": 10,
        "fetched_at": "2026-10-01T00:00:00Z",
        "runs": value,
        "wickets": None,
    }


def quarter(pid, year, q, value):
    return {
        "player_id": pid,
        "player_name": "Same name",
        "year": year,
        "quarter": q,
        "average_runs": value,
        "batting_matches": 3,
    }


def test_ranking_chart_preserves_values_ids_order_and_twenty_cap():
    rows = [career(i, i * 10) for i in range(1, 26)]
    figure = ranking_bar(rows, "Runs", "SAMPLE · TEST · source")
    assert list(figure.data[0].x) == list(range(10, 201, 10))
    assert figure.data[0].y[0] == "Same name · #1"
    assert figure.layout.yaxis.autorange == "reversed"
    assert "SAMPLE" in figure.layout.title.text
    assert "source" in figure.layout.title.text


def test_comparison_unknowns_not_zero_and_no_normalization():
    figure = player_comparison(
        [career(1, 0), career(2, 100)], "wickets", "Career wickets", "SAMPLE"
    )
    assert list(figure.data[0].y) == [None, None]
    runs = player_comparison(
        [career(1, 0), career(2, 100)], "runs", "Career runs", "SAMPLE"
    )
    assert list(runs.data[0].y) == [0, 100]


def test_quarterly_gap_is_explicit_blank_and_never_connected():
    figure = quarterly_line(
        [quarter(1, 2024, 4, 10), quarter(1, 2025, 2, 20)],
        "average_runs",
        "Runs",
        "SAMPLE",
    )
    assert list(figure.data[0].x) == ["2024 Q4", "2025 Q1", "2025 Q2"]
    assert list(figure.data[0].y) == [10, None, 20]
    assert figure.data[0].connectgaps is False


def test_heatmap_keeps_stable_identities_and_unknown_zero_separate():
    rows = [quarter(1, 2024, 1, 0), quarter(2, 2024, 2, 50)]
    figure = quarterly_heatmap(rows, "average_runs", "Runs", "SAMPLE")
    assert list(figure.data[0].y) == ["Same name · #1", "Same name · #2"]
    assert [list(r) for r in figure.data[0].z] == [[0, None], [None, 50]]
    assert figure.data[0].hoverongaps is False


def test_venue_chart_does_not_merge_same_named_records():
    rows = [
        {
            "player_name": "Same",
            "venue_name": "Ground",
            "matches_played": 3,
            "total_wickets": v,
        }
        for v in (0, 20, None)
    ]
    figure = venue_bar(rows, "total_wickets", "Wickets", "SAMPLE")
    assert list(figure.data[0].x) == [0, 20]
    assert len(set(figure.data[0].y)) == 2
    assert list(figure.data[0].customdata) == [3, 3]


def test_scatter_retains_zero_dispersion_and_sample_count():
    rows = [
        {
            "player_name": "A",
            "average_runs": 0,
            "standard_deviation_runs": 0,
            "eligible_innings": 1,
        },
        {
            "player_name": "B",
            "average_runs": None,
            "standard_deviation_runs": 10,
            "eligible_innings": 5,
        },
    ]
    figure = consistency_scatter(rows, "SAMPLE")
    assert list(figure.data[0].x) == [0]
    assert list(figure.data[0].y) == [0]
    assert list(figure.data[0].customdata) == [1]


@pytest.mark.parametrize(
    "builder",
    [
        lambda: ranking_bar([], "Runs", "SAMPLE"),
        lambda: quarterly_line([], "average_runs", "Runs", "SAMPLE"),
        lambda: quarterly_heatmap([], "average_runs", "Runs", "SAMPLE"),
    ],
)
def test_empty_figures_are_serializable(builder):
    assert builder().to_json()


def test_top_players_actual_ui_renders_rank_and_comparison_charts(
    settings, monkeypatch
):
    monkeypatch.setattr("ui.top_players.load_settings", lambda: settings)
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("No HTTP")
    ) as network:
        at = AppTest.from_file(
            str(PROJECT_ROOT / "pages/03_Top_Players.py"), default_timeout=20
        ).run()
        assert not at.exception
        assert len(at.get("plotly_chart")) == 3
        at.multiselect(key="chart_compare_players").set_value([12]).run()
        assert len(at.get("plotly_chart")) == 1 and not at.exception
        assert not network.called


@pytest.mark.parametrize(
    "view,count",
    [
        ("Quarterly trends and heatmap (Q25)", 2),
        ("Consistency scatter (Q19)", 1),
        ("Venue comparison (Q14)", 1),
    ],
)
def test_analytics_visualizations_use_saved_sql_without_network(
    settings, monkeypatch, view, count
):
    monkeypatch.setattr("ui.analytics.load_settings", lambda: settings)
    with patch(
        "requests.sessions.Session.send", side_effect=AssertionError("No HTTP")
    ) as network:
        at = AppTest.from_file(
            str(PROJECT_ROOT / "pages/04_Analytics.py"), default_timeout=20
        ).run()
        at.radio(key="analytics_workspace").set_value("Visualizations").run()
        at.selectbox(key="viz_analysis").select(view).run()
        assert not at.exception
        assert len(at.get("plotly_chart")) == count
        assert not network.called


def test_empty_chart_state_no_fabrication(settings, database, monkeypatch):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")
    monkeypatch.setattr("ui.analytics.load_settings", lambda: settings)
    at = AppTest.from_file(
        str(PROJECT_ROOT / "pages/04_Analytics.py"), default_timeout=20
    ).run()
    at.radio(key="analytics_workspace").set_value("Visualizations").run()
    assert not at.exception and not at.get("plotly_chart")
    assert any("No qualifying saved data" in x.value for x in at.info)
