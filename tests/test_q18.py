"""Q18 limited-overs eligibility, average workload and pooled economy."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q18_limited_overs_economy.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql(
        "UPDATE bowling_performances SET legal_balls=0,runs_conceded=0,wickets=0,maidens=0"
    )
    c.exec_driver_sql("UPDATE matches SET format_id=2 WHERE match_id<=11")


def figures(c, mid, balls=12, runs=12, wickets=1, pid=7):
    inning = c.exec_driver_sql(
        "SELECT innings_id FROM bowling_performances WHERE player_id=? AND match_id=? ORDER BY innings_id LIMIT 1",
        (pid, mid),
    ).scalar_one()
    c.exec_driver_sql(
        "UPDATE bowling_performances SET legal_balls=?,runs_conceded=?,wickets=? WHERE player_id=? AND innings_id=?",
        (balls, runs, wickets, pid, inning),
    )
    return inning


def test_mixed_formats_pooled_rate_and_two_overs_average_not_each_match(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 11):
            figures(
                c,
                mid,
                6 if mid <= 5 else 18,
                6 if mid <= 5 else 36,
                1 if mid <= 5 else 2,
            )
        c.exec_driver_sql(
            "UPDATE matches SET format_id=3 WHERE match_id BETWEEN 6 AND 10"
        )
    row = run(database)[0]
    assert row["matches_bowled"] == 10 and row["average_overs_per_match"] == 2.0
    assert row["overall_economy_rate"] == 10.5  # Pooled 6*210/120, not mean economy 9.
    assert row["total_wickets"] == 15


def test_ten_matches_and_exact_average_ball_boundary(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 10):
            figures(c, mid)
    assert run(database) == []
    with database.transaction(write=True) as c:
        figures(c, 10, 11)
    assert run(database) == []  # 119 legal balls / ten matches is below two overs.
    with database.transaction(write=True) as c:
        figures(c, 10, 12)
    assert run(database)[0]["average_overs_per_match"] == 2.0


def test_multiple_innings_do_not_inflate_match_count(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 10):
            figures(c, mid)
        figures(c, 1, 6, 6, 1)
        number = c.exec_driver_sql(
            "SELECT MAX(innings_number)+1 FROM innings WHERE match_id=1"
        ).scalar_one()
        inserted = c.exec_driver_sql(
            "INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id) VALUES(1,?,1,2)",
            (number,),
        )
        c.exec_driver_sql(
            "INSERT INTO bowling_performances(innings_id,player_id,match_id,team_id,legal_balls,runs_conceded,wickets,updated_at) VALUES(?,7,1,2,6,6,1,'2026-10-01T00:00:00Z')",
            (inserted.lastrowid,),
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        figures(c, 10)
    assert run(database)[0]["matches_bowled"] == 10


def test_test_format_and_zero_bowling_placeholders_do_not_qualify(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 11):
            figures(c, mid)
        c.exec_driver_sql("UPDATE matches SET format_id=1 WHERE match_id=10")
    assert (
        run(database) == []
    )  # Nine limited-overs matches; other zero rows don't count.


def test_unknown_totals_preserved_and_unknown_balls_prevent_workload_claim(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 11):
            figures(c, mid)
        figures(c, 1, 12, None, 1)
        figures(c, 2, 12, 12, None)
    row = run(database)[0]
    assert row["overall_economy_rate"] is None and row["total_wickets"] is None
    assert row["matches_bowled"] == 10
    with database.transaction(write=True) as c:
        figures(c, 1, None, 12, 1)
    assert run(database) == []


def test_deleted_rows_players_and_superovers_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 11):
            figures(c, mid)
        inning = figures(c, 1)
        c.exec_driver_sql(
            "UPDATE bowling_performances SET is_deleted=1 WHERE player_id=7 AND innings_id=?",
            (inning,),
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE bowling_performances SET is_deleted=0 WHERE player_id=7 AND innings_id=?",
            (inning,),
        )
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=1 WHERE innings_id=?", (inning,)
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=0 WHERE innings_id=?", (inning,)
        )
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=7")
    assert run(database) == []


def test_lowest_economy_first_with_separate_equal_named_bowlers(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 11):
            figures(c, mid, 24, 12, 1, pid=7)
            figures(c, mid, 24, 24, 2, pid=8)
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name' WHERE player_id IN(7,8)"
        )
    rows = run(database)
    assert len(rows) == 2 and [r["overall_economy_rate"] for r in rows] == [3.0, 6.0]
