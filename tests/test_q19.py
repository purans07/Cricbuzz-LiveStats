"""Q19 innings eligibility, population deviation and numerical stability."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q19_batting_consistency.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")
    c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id<>1")


def score(c, mid, runs, balls=10, pid=1, date="2023-06-01T00:00:00Z"):
    c.exec_driver_sql("UPDATE matches SET starts_at=? WHERE match_id=?", (date, mid))
    inning = c.exec_driver_sql(
        "SELECT innings_id FROM batting_performances WHERE player_id=? AND match_id=? ORDER BY innings_id LIMIT 1",
        (pid, mid),
    ).scalar_one()
    c.exec_driver_sql(
        "UPDATE batting_performances SET is_deleted=0,runs=?,balls_faced=?,fours=0,sixes=0 WHERE player_id=? AND innings_id=?",
        (runs, balls, pid, inning),
    )
    return inning


def test_population_mean_and_standard_deviation_not_sample_deviation(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid, runs in [(1, 10), (2, 20), (3, 30)]:
            score(c, mid, runs)
    assert run(database) == [
        {
            "player_name": "Sample Player 01",
            "eligible_innings": 3,
            "average_runs": 20.0,
            "standard_deviation_runs": 8.16,
        }
    ]


def test_date_ball_boundary_unknown_runs_and_singleton_zero(database):
    with database.transaction(write=True) as c:
        isolate(c)
        score(c, 1, 0, 10, date="2022-01-01T00:00:00Z")
        score(c, 2, 100, 10, date="2021-12-31T23:59:59Z")
        score(c, 3, 100, 9)
        score(c, 4, None, 10)
        score(c, 5, 100, None)
        score(c, 6, 100)
        c.exec_driver_sql("UPDATE matches SET starts_at=NULL WHERE match_id=6")
    row = run(database)[0]
    assert row["eligible_innings"] == 1
    assert row["average_runs"] == row["standard_deviation_runs"] == 0.0


def test_separate_innings_in_one_match_are_not_collapsed_to_match_total(database):
    with database.transaction(write=True) as c:
        isolate(c)
        score(c, 1, 10)
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
    row = run(database)[0]
    assert row["eligible_innings"] == 2 and row["average_runs"] == 20.0
    assert row["standard_deviation_runs"] == 10.0


def test_active_profile_performance_and_superover_filters(database):
    with database.transaction(write=True) as c:
        isolate(c)
        inning = score(c, 1, 10)
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE player_id=1 AND innings_id=?",
            (inning,),
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        score(c, 1, 10)
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=0 WHERE player_id=1")
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=1 WHERE innings_id=?", (inning,)
        )
    assert run(database) == []


def test_consistency_order_preserves_equal_named_identities(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "UPDATE players SET is_deleted=0,full_name='Same Name' WHERE player_id IN(1,2)"
        )
        score(c, 1, 10, pid=1)
        score(c, 2, 10, pid=1)
        score(c, 1, 0, pid=2)
        score(c, 2, 20, pid=2)
    rows = run(database)
    assert len(rows) == 2
    assert [r["standard_deviation_runs"] for r in rows] == [0.0, 10.0]
    assert all(r["eligible_innings"] == 2 for r in rows)


def test_centered_variance_avoids_large_offset_cancellation(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 5):
            score(c, mid, 1_000_000_000 + mid - 1)
    row = run(database)[0]
    assert row["average_runs"] == 1_000_000_001.5
    assert row["standard_deviation_runs"] == 1.12
