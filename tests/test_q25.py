"""Quarterly eligibility, gaps, mean rates and transparent trend rules."""

from pathlib import Path

import pytest
from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q25_quarterly_player_evolution.sql"
).read_text()
PARAMS = {"window_start": "2023-10-01T00:00:00Z", "window_end": "2026-10-01T00:00:00Z"}


def run(db, **params):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY), PARAMS | params).mappings()]


def history(c, values, quarter_numbers=None, balls=50):
    c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")
    for offset, runs in enumerate(values):
        q = offset if quarter_numbers is None else quarter_numbers[offset]
        for j in range(3):
            mid = offset * 3 + j + 1
            date = f"{2024 + q // 4}-{(q % 4) * 3 + 1:02}-{j + 1:02}T00:00:00Z"
            c.exec_driver_sql(
                "UPDATE matches SET starts_at=?,status='completed' WHERE match_id=?",
                (date, mid),
            )
            iid = c.exec_driver_sql(
                "SELECT MIN(innings_id) FROM batting_performances WHERE player_id=1 AND match_id=?",
                (mid,),
            ).scalar_one()
            c.exec_driver_sql(
                "UPDATE batting_performances SET is_deleted=0,runs=?,balls_faced=?,fours=0,sixes=0 WHERE player_id=1 AND innings_id=?",
                (runs, balls, iid),
            )


@pytest.mark.parametrize(
    "values,phase,trend,slope",
    [
        ([10, 20, 30, 40, 50, 60], "Career Ascending", "Improving", 10),
        ([60, 50, 40, 30, 20, 10], "Career Declining", "Declining", -10),
        ([30] * 6, "Career Stable", "Stable", 0),
    ],
)
def test_quarterly_and_ols_career_trends(database, values, phase, trend, slope):
    with database.transaction(write=True) as c:
        history(c, values)
    rows = run(database)
    assert len(rows) == 6
    assert all(r["career_phase"] == phase for r in rows)
    assert rows[0]["quarterly_trend"] is None
    assert rows[1]["quarterly_trend"] == trend
    assert rows[1]["runs_slope_per_quarter"] == slope
    assert rows[0]["comparison_status"] == "first_observed_quarter"


def test_minimum_six_quarters_and_all_observed_quarters_have_three_matches(database):
    with database.transaction(write=True) as c:
        history(c, [30] * 5)
    assert run(database) == []
    with database.transaction(write=True) as c:
        history(c, [30] * 6)
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE player_id=1 AND match_id=18"
        )
    assert run(database) == []


def test_quarter_gap_not_previous_calendar_quarter_and_ols_uses_elapsed_time(database):
    with database.transaction(write=True) as c:
        history(c, [10, 20, 30, 50, 60, 70], quarter_numbers=[0, 1, 2, 4, 5, 6])
    rows = run(database)
    assert rows[3]["comparison_status"] == "quarter_gap"
    assert rows[3]["runs_change"] is None
    assert rows[3]["quarterly_trend"] is None
    assert rows[0]["runs_slope_per_quarter"] == 10


@pytest.mark.parametrize("column", ["runs", "balls_faced"])
def test_missing_metric_preserves_quarter_and_withholds_career_label(database, column):
    with database.transaction(write=True) as c:
        history(c, [30] * 6)
        c.exec_driver_sql(
            f"UPDATE batting_performances SET {column}=NULL WHERE player_id=1 AND match_id=7"
        )
    rows = run(database)
    assert len(rows) == 6
    assert all(r["career_phase"] is None for r in rows)
    assert rows[2]["average_strike_rate"] is None
    assert (
        rows[2]["comparison_status"]
        == rows[3]["comparison_status"]
        == "incomplete_metrics"
    )


def test_mean_of_match_rates_not_pooled_rate_and_zero_balls(database):
    with database.transaction(write=True) as c:
        history(c, [30] * 6)
        c.exec_driver_sql(
            "UPDATE batting_performances SET balls_faced=10 WHERE player_id=1 AND match_id=1"
        )
    assert run(database)[0]["average_strike_rate"] == 140  # (300+60+60)/3
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE batting_performances SET balls_faced=0 WHERE player_id=1 AND match_id=1"
        )
    assert run(database)[0]["average_strike_rate"] is None
    assert run(database)[0]["career_phase"] is None


def test_whole_quarter_bounds_inclusive_start_exclusive_end(database):
    with database.transaction(write=True) as c:
        history(c, [30] * 7)
    rows = run(
        database, window_start="2024-04-01T00:00:00Z", window_end="2025-10-01T00:00:00Z"
    )
    assert len(rows) == 6
    assert (rows[0]["year"], rows[0]["quarter"]) == (2024, 2)
    assert (rows[-1]["year"], rows[-1]["quarter"]) == (2025, 3)


def test_inactive_profile_superover_and_unfinished_matches_excluded(database):
    with database.transaction(write=True) as c:
        history(c, [30] * 6)
        c.exec_driver_sql("UPDATE matches SET status='live' WHERE match_id=1")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='completed' WHERE match_id=1")
        c.exec_driver_sql("UPDATE innings SET is_super_over=1 WHERE match_id=1")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE innings SET is_super_over=0 WHERE match_id=1")
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert run(database) == []


def test_conflicting_metrics_are_stable_and_exact_threshold_is_not_exceeded(database):
    with database.transaction(write=True) as c:
        history(c, [10, 20, 30, 40, 50, 60])
        for offset in range(6):
            c.exec_driver_sql(
                "UPDATE batting_performances SET balls_faced=? WHERE player_id=1 AND match_id BETWEEN ? AND ?",
                ((offset + 1) * 10 * (offset + 1), offset * 3 + 1, offset * 3 + 3),
            )
    rows = run(database)
    assert rows[1]["runs_change"] > 0 and rows[1]["strike_rate_change"] < 0
    assert rows[1]["quarterly_trend"] == "Stable"
    assert rows[0]["career_phase"] == "Career Stable"
    with database.transaction(write=True) as c:
        history(c, [10, 11, 12, 13, 14, 15], balls=100)
    assert run(database)[0]["runs_slope_per_quarter"] == 1
    assert run(database)[0]["career_phase"] == "Career Stable"


def test_multiple_innings_are_one_batting_match_not_three(database):
    with database.transaction(write=True) as c:
        history(c, [30] * 6)
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE player_id=1 AND match_id IN(2,3)"
        )
        number = c.exec_driver_sql(
            "SELECT MAX(innings_number) FROM innings WHERE match_id=1"
        ).scalar_one()
        for n in (number + 1, number + 2):
            inserted = c.exec_driver_sql(
                "INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id) VALUES(1,?,1,2)",
                (n,),
            )
            c.exec_driver_sql(
                "INSERT INTO batting_performances(innings_id,player_id,match_id,team_id,runs,balls_faced,updated_at) VALUES(?,1,1,1,30,10,'2026-10-01T00:00:00Z')",
                (inserted.lastrowid,),
            )
    assert run(database) == []
