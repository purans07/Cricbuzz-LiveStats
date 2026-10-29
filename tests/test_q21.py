"""Q21 exact scoring weights, complete-case ranks and undefined denominators."""

from pathlib import Path

import pytest
from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q21_weighted_performance_rank.sql"
).read_text()
SOURCE = "Synthetic training fixture"


def run(db, source=SOURCE):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"source_name": source}).mappings()
        ]


def isolate(c):
    c.exec_driver_sql("UPDATE career_stats_snapshots SET catches=NULL WHERE batch_id=2")


def metrics(c, pid=1, fid=1, catches=10):
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET runs=1000,dismissals=20,balls_faced=1000,wickets=50,runs_conceded=1500,legal_balls_bowled=1800,catches=?,stumpings=2 WHERE player_id=? AND format_id=? AND batch_id=2",
        (catches, pid, fid),
    )


def test_exact_component_weights_and_total(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c)
    assert run(database) == [
        {
            "cricket_format": "TEST",
            "performance_rank": 1,
            "player_name": "Sample Player 01",
            "batting_points": 65.0,
            "bowling_points": 112.0,
            "fielding_points": 40.0,
            "total_points": 217.0,
        }
    ]


def test_dense_ties_and_independent_format_rankings(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c, pid=1)
        metrics(c, pid=2)
        metrics(c, pid=3, catches=11)
        metrics(c, pid=4, fid=2)
    rows = run(database)
    tests = [r for r in rows if r["cricket_format"] == "TEST"]
    assert [r["performance_rank"] for r in tests] == [1, 2, 2]
    assert (
        next(r for r in rows if r["cricket_format"] == "ODI")["performance_rank"] == 1
    )


def test_missing_fielding_is_not_zero_but_known_zero_is_valid(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET stumpings=NULL WHERE player_id=1 AND format_id=1 AND batch_id=2"
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET catches=0,stumpings=0 WHERE player_id=1 AND format_id=1 AND batch_id=2"
        )
    assert run(database)[0]["fielding_points"] == 0.0
    assert run(database)[0]["total_points"] == 177.0


@pytest.mark.parametrize(
    "column", ["dismissals", "balls_faced", "wickets", "legal_balls_bowled"]
)
def test_zero_denominator_not_replaced_with_reported_placeholders(database, column):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c)
        # Column comes from this fixed test parameter allowlist.
        c.exec_driver_sql(
            f"UPDATE career_stats_snapshots SET {column}=0,reported_batting_average=50,reported_strike_rate=100,reported_bowling_average=30,reported_economy=5 WHERE player_id=1 AND format_id=1 AND batch_id=2"
        )
    assert run(database) == []


def test_negative_bowling_points_are_not_clamped(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET wickets=1,runs_conceded=5000,legal_balls_bowled=50 WHERE player_id=1 AND format_id=1 AND batch_id=2"
        )
    assert run(database)[0]["bowling_points"] == -3661.0
    assert run(database)[0]["total_points"] == -3556.0


def test_latest_source_scope_and_deleted_players(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c)
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(98,2,'test','2026-10-03T00:00:00Z','complete','committed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,runs,dismissals,balls_faced,wickets,runs_conceded,legal_balls_bowled,catches,stumpings) VALUES(1,1,98,1000,20,1000,50,1500,1800,100,2)"
        )
    assert run(database)[0]["total_points"] == 217.0
    assert run(database, "Local operator")[0]["total_points"] == 487.0
    assert run(database, "' OR 1=1 --") == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert run(database) == []


def test_reported_ratios_only_for_unknown_denominators(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=NULL,balls_faced=NULL,legal_balls_bowled=NULL,reported_batting_average=50,reported_strike_rate=100,reported_economy=5 WHERE player_id=1 AND format_id=1 AND batch_id=2"
        )
    assert run(database)[0]["total_points"] == 217.0


def test_rounding_does_not_create_rank_ties(database):
    with database.transaction(write=True) as c:
        isolate(c)
        metrics(c, pid=1)
        metrics(c, pid=2)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=NULL,reported_batting_average=100.0001 WHERE player_id=1 AND format_id=1 AND batch_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=NULL,reported_batting_average=100.0002 WHERE player_id=2 AND format_id=1 AND batch_id=2"
        )
    rows = run(database)
    assert [r["player_name"] for r in rows] == ["Sample Player 02", "Sample Player 01"]
    assert [r["performance_rank"] for r in rows] == [1, 2]
    assert rows[0]["total_points"] == rows[1]["total_points"]
