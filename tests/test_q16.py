"""Q16 calendar eligibility, appearance denominators and mean match strike rate."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q16_yearly_batting.sql").read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id<>1")
    c.exec_driver_sql("UPDATE matches SET status='scheduled'")
    c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")


def appearance(c, mid, year=2021):
    c.exec_driver_sql(
        "UPDATE matches SET status='completed',starts_at=? WHERE match_id=?",
        (f"{year}-06-01T00:00:00Z", mid),
    )


def batting(c, mid, runs=10, balls=20):
    inning = c.exec_driver_sql(
        "SELECT innings_id FROM batting_performances WHERE player_id=1 AND match_id=? ORDER BY innings_id LIMIT 1",
        (mid,),
    ).scalar_one()
    c.exec_driver_sql(
        "UPDATE batting_performances SET is_deleted=0,runs=?,balls_faced=?,fours=0,sixes=0 WHERE player_id=1 AND innings_id=?",
        (runs, balls, inning),
    )
    return inning


def test_since_2020_boundary_and_unknown_dates(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 8):
            appearance(c, mid, 2020)
            batting(c, mid)
        c.exec_driver_sql(
            "UPDATE matches SET starts_at='2019-12-31T23:59:59Z' WHERE match_id=1"
        )
        c.exec_driver_sql(
            "UPDATE matches SET starts_at='2020-01-01T00:00:00Z' WHERE match_id=2"
        )
        c.exec_driver_sql("UPDATE matches SET starts_at=NULL WHERE match_id=7")
    assert run(database) == [
        {
            "player_name": "Sample Player 01",
            "match_year": 2020,
            "matches_played": 5,
            "average_runs_per_match": 10.0,
            "average_strike_rate": 50.0,
        }
    ]


def test_five_matches_required_within_each_year_not_across_years(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 6):
            appearance(c, mid, 2021 if mid < 5 else 2022)
            batting(c, mid)
    assert run(database) == []
    with database.transaction(write=True) as c:
        appearance(c, 5, 2021)
    assert run(database)[0]["matches_played"] == 5


def test_multi_innings_match_totals_and_arithmetic_mean_strike_rate(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 6):
            appearance(c, mid)
            batting(c, mid)
        batting(c, 1, 20, 20)
        number = c.exec_driver_sql(
            "SELECT MAX(innings_number)+1 FROM innings WHERE match_id=1"
        ).scalar_one()
        result = c.exec_driver_sql(
            "INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id) VALUES(1,?,1,2)",
            (number,),
        )
        c.exec_driver_sql(
            "INSERT INTO batting_performances(innings_id,player_id,match_id,team_id,runs,balls_faced,updated_at) VALUES(?,1,1,1,30,10,'2026-10-01T00:00:00Z')",
            (result.lastrowid,),
        )
    row = run(database)[0]
    assert row["matches_played"] == 5
    assert row["average_runs_per_match"] == 18.0  # (50+10+10+10+10)/5.
    assert row["average_strike_rate"] == 73.33  # Mean of 166.666... and four 50s.


def test_missing_batting_unknown_balls_and_known_zero_denominators(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 6):
            appearance(c, mid)
            if mid < 5:
                batting(c, mid)
    row = run(database)[0]
    assert row["matches_played"] == 5
    assert row["average_runs_per_match"] is None and row["average_strike_rate"] is None
    with database.transaction(write=True) as c:
        batting(c, 5, 0, 0)
    row = run(database)[0]
    assert row["average_runs_per_match"] == 8.0 and row["average_strike_rate"] == 50.0
    with database.transaction(write=True) as c:
        batting(c, 5, 0, None)
    assert run(database)[0]["average_strike_rate"] is None


def test_substitute_only_is_not_an_appearance_without_batting_evidence(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 6):
            appearance(c, mid)
            if mid < 5:
                batting(c, mid)
        c.exec_driver_sql(
            "UPDATE match_players SET participation='substitute' WHERE player_id=1 AND match_id=5"
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        batting(c, 5)
    assert run(database)[0]["matches_played"] == 5


def test_deleted_batting_and_superovers_do_not_become_zero_and_deleted_profiles_excluded(
    database,
):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in range(1, 6):
            appearance(c, mid)
            batting(c, mid)
        inning = batting(c, 1)
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=1 WHERE innings_id=?", (inning,)
        )
    assert run(database)[0]["average_runs_per_match"] is None
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=0 WHERE innings_id=?", (inning,)
        )
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE player_id=1 AND innings_id=?",
            (inning,),
        )
    assert run(database)[0]["average_runs_per_match"] is None
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert run(database) == []
