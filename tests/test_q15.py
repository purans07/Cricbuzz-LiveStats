"""Q15 unit-specific margins, batting match grain and historical team wins."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q15_close_match_batting.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql(
        "UPDATE matches SET winner_team_id=NULL,result_type='pending',margin_value=NULL,margin_unit=NULL"
    )
    c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")


def close(c, mid, margin=1, unit="runs", winner=1):
    c.exec_driver_sql(
        "UPDATE matches SET status='completed',result_type='win',winner_team_id=?,margin_value=?,margin_unit=? WHERE match_id=?",
        (winner, margin, unit, mid),
    )


def batter(c, mid, runs=10, pid=1):
    inning = c.exec_driver_sql(
        "SELECT innings_id FROM batting_performances WHERE player_id=? AND match_id=? ORDER BY innings_id LIMIT 1",
        (pid, mid),
    ).scalar_one()
    c.exec_driver_sql(
        "UPDATE batting_performances SET is_deleted=0,runs=?,fours=0,sixes=0 WHERE player_id=? AND innings_id=?",
        (runs, pid, inning),
    )
    return inning


def test_strict_run_and_wicket_boundaries(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid, amount, unit in [
            (1, 49, "runs"),
            (2, 50, "runs"),
            (3, 4, "wickets"),
            (4, 5, "wickets"),
        ]:
            close(c, mid, amount, unit)
            batter(c, mid)
    row = run(database)[0]
    assert row["total_close_matches_played"] == 2
    assert row["team_wins_when_batted"] == 2 and row["average_runs"] == 10


def test_multiple_innings_sum_to_one_match_and_average_match_totals(database):
    with database.transaction(write=True) as c:
        isolate(c)
        close(c, 1)
        batter(c, 1, 20)
        number = c.exec_driver_sql(
            "SELECT MAX(innings_number)+1 FROM innings WHERE match_id=1"
        ).scalar_one()
        result = c.exec_driver_sql(
            "INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id) VALUES(1,?,1,2)",
            (number,),
        )
        c.exec_driver_sql(
            "INSERT INTO batting_performances(innings_id,player_id,match_id,team_id,runs,updated_at) VALUES(?,1,1,1,30,'2026-10-01T00:00:00Z')",
            (result.lastrowid,),
        )
        close(c, 2, winner=2)
        batter(c, 2, 10)
    assert run(database) == [
        {
            "player_name": "Sample Player 01",
            "average_runs": 30.0,
            "total_close_matches_played": 2,
            "team_wins_when_batted": 1,
        }
    ]


def test_unknown_runs_prevent_partial_average_but_not_match_and_win_counts(database):
    with database.transaction(write=True) as c:
        isolate(c)
        close(c, 1)
        close(c, 2)
        batter(c, 1, None)
        batter(c, 2, 10)
    row = run(database)[0]
    assert row["average_runs"] is None
    assert row["total_close_matches_played"] == row["team_wins_when_batted"] == 2


def test_unfinished_unresolved_draws_and_unknown_margins_are_not_close_wins(database):
    with database.transaction(write=True) as c:
        isolate(c)
        close(c, 1)
        c.exec_driver_sql("UPDATE matches SET status='live' WHERE match_id=1")
        close(c, 2)
        c.exec_driver_sql(
            "UPDATE matches SET margin_value=NULL,margin_unit=NULL WHERE match_id=2"
        )
        c.exec_driver_sql(
            "UPDATE matches SET status='completed',result_type='draw' WHERE match_id=3"
        )
        c.exec_driver_sql("UPDATE matches SET status='completed' WHERE match_id=4")
        for mid in (1, 2, 3, 4):
            batter(c, mid)
    assert run(database) == []


def test_active_batting_and_ordinary_innings_evidence_required(database):
    with database.transaction(write=True) as c:
        isolate(c)
        close(c, 1)
        inning = batter(c, 1)
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE player_id=1 AND innings_id=?",
            (inning,),
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        batter(c, 1)
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=0 WHERE player_id=1")
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=1 WHERE innings_id=?", (inning,)
        )
    assert run(database) == []


def test_same_names_stay_separate_and_only_batting_team_wins_count(database):
    with database.transaction(write=True) as c:
        isolate(c)
        close(c, 1, winner=1)
        batter(c, 1, pid=1)
        batter(c, 1, pid=7)
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name' WHERE player_id IN(1,7)"
        )
    rows = run(database)
    assert len(rows) == 2
    assert [r["team_wins_when_batted"] for r in rows] == [1, 0]
    assert all(r["total_close_matches_played"] == 1 for r in rows)
