"""Recent form window, aggregate grain, completeness and explicit heuristic."""

from pathlib import Path

import pytest
from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q23_recent_player_form.sql"
).read_text()


def run(db, cutoff="2026-10-01T00:00:00Z"):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"as_of_utc": cutoff}).mappings()
        ]


def isolate(c, scores, balls=50):
    c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")
    for mid, runs in enumerate(scores, 1):
        c.exec_driver_sql(
            "UPDATE matches SET starts_at=?,status='completed' WHERE match_id=?",
            (f"2026-09-{mid:02}T00:00:00Z", mid),
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
    "scores,label",
    [
        ([60] * 10, "Excellent Form"),
        ([40] * 9 + [60], "Good Form"),
        ([20] * 10, "Average Form"),
        ([0] * 10, "Poor Form"),
    ],
)
def test_four_documented_categories(database, scores, label):
    with database.transaction(write=True) as c:
        isolate(c, scores)
    r = run(database)[0]
    assert r["form_category"] == label
    assert r["coverage_status"] == "classified"


def test_last_five_last_ten_and_population_deviation(database):
    with database.transaction(write=True) as c:
        isolate(c, [0] * 5 + [60] * 5)
    r = run(database)[0]
    assert r["average_runs_last_5"] == 60
    assert r["average_runs_last_10"] == 30
    assert r["standard_deviation_runs"] == 30
    assert r["consistency_score"] == 45.45
    assert r["strike_rate_last_5"] == 120
    assert r["strike_rate_last_10"] == 60
    assert r["scores_above_50_last_5"] == r["scores_above_50_last_10"] == 5


def test_threshold_strictly_above_fifty_and_short_history(database):
    with database.transaction(write=True) as c:
        isolate(c, [50] * 5)
    r = run(database)[0]
    assert r["scores_above_50_last_10"] == 0
    assert r["form_category"] is None
    assert r["coverage_status"] == "insufficient_history"
    assert r["standard_deviation_runs"] == 0


@pytest.mark.parametrize("column", ["runs", "balls_faced"])
def test_missing_metrics_not_skipped_or_backfilled(database, column):
    with database.transaction(write=True) as c:
        isolate(c, [60] * 11)
        c.exec_driver_sql(
            f"UPDATE batting_performances SET {column}=NULL WHERE player_id=1 AND match_id=11"
        )
    r = run(database)[0]
    assert r["matches_last_10"] == 10
    assert r["form_category"] is None
    assert r["coverage_status"] == "incomplete_metrics"


def test_zero_ball_denominator_is_undefined(database):
    with database.transaction(write=True) as c:
        isolate(c, [0] * 10, balls=0)
    assert run(database)[0]["strike_rate_last_10"] is None
    assert run(database)[0]["form_category"] is None


def test_cutoff_status_unknown_date_tombstone_and_super_over(database):
    with database.transaction(write=True) as c:
        isolate(c, [60] * 10)
        c.exec_driver_sql("UPDATE matches SET status='live' WHERE match_id=1")
        c.exec_driver_sql("UPDATE matches SET starts_at=NULL WHERE match_id=2")
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE player_id=1 AND match_id=3"
        )
        c.exec_driver_sql("UPDATE innings SET is_super_over=1 WHERE match_id=4")
    assert run(database, cutoff="2026-09-10T00:00:00Z")[0]["matches_last_10"] == 5
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert run(database) == []


def test_tie_order_uses_match_id_and_only_last_ten(database):
    with database.transaction(write=True) as c:
        isolate(c, [1000] + [20] * 10)
        c.exec_driver_sql("UPDATE matches SET starts_at='2026-09-01T00:00:00Z'")
    r = run(database)[0]
    assert r["matches_last_10"] == 10
    assert r["average_runs_last_10"] == 20


def test_strike_rate_is_pooled_not_average_of_rates(database):
    with database.transaction(write=True) as c:
        isolate(c, [10, 90])
        c.exec_driver_sql(
            "UPDATE batting_performances SET balls_faced=10 WHERE player_id=1 AND match_id=1"
        )
        c.exec_driver_sql(
            "UPDATE batting_performances SET balls_faced=30 WHERE player_id=1 AND match_id=2"
        )
    assert run(database)[0]["strike_rate_last_10"] == 250


def test_two_test_innings_are_one_match_performance(database):
    with database.transaction(write=True) as c:
        isolate(c, [10])
        number = c.exec_driver_sql(
            "SELECT MAX(innings_number)+1 FROM innings WHERE match_id=1"
        ).scalar_one()
        inserted = c.exec_driver_sql(
            "INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id) VALUES(1,?,1,2)",
            (number,),
        )
        c.exec_driver_sql(
            "INSERT INTO batting_performances(innings_id,player_id,match_id,team_id,runs,balls_faced,updated_at) VALUES(?,1,1,1,30,10,'2026-10-01T00:00:00Z')",
            (inserted.lastrowid,),
        )
    r = run(database)[0]
    assert r["matches_last_10"] == 1
    assert r["average_runs_last_10"] == 40
    assert r["strike_rate_last_10"] == 66.67
