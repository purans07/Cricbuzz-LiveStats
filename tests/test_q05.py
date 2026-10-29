"""Q05 win counts, zero-win teams, match grain and result eligibility."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q05_team_wins.sql").read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def clear_results(c):
    c.exec_driver_sql(
        "UPDATE matches SET winner_team_id=NULL,result_type='pending',margin_value=NULL,margin_unit=NULL"
    )


def win(c, mid, team=1, status="completed"):
    c.exec_driver_sql(
        "UPDATE matches SET winner_team_id=?,result_type='win',status=? WHERE match_id=?",
        (team, status, mid),
    )


def test_known_counts_largest_first_and_zero_win_teams(database):
    with database.transaction(write=True) as c:
        clear_results(c)
        win(c, 1, 1)
        win(c, 2, 1)
        win(c, 3, 2)
        c.exec_driver_sql(
            "INSERT INTO teams(team_id,name,is_international) VALUES(30,'Fictional Winless Team',0)"
        )
    assert run(database) == [
        {"team_name": "Sample India XI", "total_wins": 2},
        {"team_name": "Sample Australia XI", "total_wins": 1},
        {"team_name": "Fictional Winless Team", "total_wins": 0},
    ]


def test_noncompleted_wins_do_not_count(database):
    with database.transaction(write=True) as c:
        clear_results(c)
        for mid, status in [
            (1, "live"),
            (2, "scheduled"),
            (3, "abandoned"),
            (4, "unknown"),
        ]:
            win(c, mid, 1, status)
    assert all(row["total_wins"] == 0 for row in run(database))


def test_draw_tie_no_result_and_pending_do_not_count(database):
    with database.transaction(write=True) as c:
        clear_results(c)
        for mid, result in [(1, "draw"), (2, "tie"), (3, "no_result"), (4, "pending")]:
            c.exec_driver_sql(
                "UPDATE matches SET status='completed',result_type=? WHERE match_id=?",
                (result, mid),
            )
    assert len(run(database)) == 2
    assert all(row["total_wins"] == 0 for row in run(database))


def test_multiple_innings_do_not_multiply_wins(database):
    with database.transaction(write=True) as c:
        clear_results(c)
        win(c, 1)
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM innings WHERE match_id=1"
            ).scalar_one()
            >= 2
        )
    assert sum(r["total_wins"] for r in run(database)) == 1


def test_same_names_preserve_team_identities_and_stable_ties(database):
    with database.transaction(write=True) as c:
        clear_results(c)
        win(c, 1, 1)
        win(c, 2, 2)
        c.exec_driver_sql("UPDATE teams SET name='Same Name' WHERE team_id IN(1,2)")
    assert run(database) == [
        {"team_name": "Same Name", "total_wins": 1},
        {"team_name": "Same Name", "total_wins": 1},
    ]
