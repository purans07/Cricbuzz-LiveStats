"""Q12 country equality, unknown evidence and completed-win match grain."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q12_home_away_wins.sql").read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def setup(c):
    c.exec_driver_sql(
        "UPDATE matches SET winner_team_id=NULL,result_type='pending',margin_value=NULL,margin_unit=NULL"
    )
    c.exec_driver_sql(
        "INSERT INTO venues(venue_id,name,country_id) VALUES(90,'Fictional India Venue',1),(91,'Fictional Australia Venue',2)"
    )


def win(c, mid, team, venue):
    c.exec_driver_sql(
        "UPDATE matches SET status='completed',winner_team_id=?,result_type='win',venue_id=? WHERE match_id=?",
        (team, venue, mid),
    )


def test_known_home_away_counts_and_zero_win_team(database):
    with database.transaction(write=True) as c:
        setup(c)
        win(c, 1, 1, 90)
        win(c, 2, 1, 90)
        win(c, 3, 1, 91)
        win(c, 4, 2, 91)
        win(c, 5, 2, 90)
        c.exec_driver_sql(
            "INSERT INTO teams(team_id,name,country_id,is_international) VALUES(80,'Fictional Winless Team',NULL,1)"
        )
    rows = {r["team_name"]: r for r in run(database)}
    assert rows["Sample India XI"] == {
        "team_name": "Sample India XI",
        "home_wins": 2,
        "away_wins": 1,
        "unclassified_wins": 0,
    }
    assert (
        rows["Sample Australia XI"]["home_wins"] == 1
        and rows["Sample Australia XI"]["away_wins"] == 1
    )
    assert rows["Fictional Winless Team"]["unclassified_wins"] == 0


def test_missing_team_or_venue_country_and_missing_venue_are_unclassified(database):
    with database.transaction(write=True) as c:
        setup(c)
        c.exec_driver_sql("UPDATE teams SET country_id=NULL WHERE team_id=1")
        win(c, 1, 1, 90)
        win(c, 2, 2, None)
        c.exec_driver_sql(
            "INSERT INTO venues(venue_id,name) VALUES(92,'Fictional Unknown Country')"
        )
        win(c, 3, 2, 92)
    rows = run(database)
    assert sum(r["home_wins"] + r["away_wins"] for r in rows) == 0
    assert sum(r["unclassified_wins"] for r in rows) == 3


def test_neutral_country_is_away_under_question_rule(database):
    with database.transaction(write=True) as c:
        setup(c)
        c.exec_driver_sql(
            "INSERT INTO countries(country_id,name) VALUES(90,'Fictional Neutral Country')"
        )
        c.exec_driver_sql(
            "INSERT INTO venues(venue_id,name,country_id) VALUES(93,'Fictional Neutral Venue',90)"
        )
        win(c, 1, 1, 93)
    assert (
        next(r for r in run(database) if r["team_name"] == "Sample India XI")[
            "away_wins"
        ]
        == 1
    )


def test_domestic_teams_and_unfinished_results_do_not_count(database):
    with database.transaction(write=True) as c:
        setup(c)
        c.exec_driver_sql("UPDATE teams SET is_international=0 WHERE team_id=2")
        win(c, 1, 2, 91)
        win(c, 2, 1, 90)
        c.exec_driver_sql("UPDATE matches SET status='live' WHERE match_id=2")
    rows = run(database)
    assert len(rows) == 1 and rows[0]["home_wins"] == 0


def test_draw_tie_pending_and_no_result_do_not_count(database):
    with database.transaction(write=True) as c:
        setup(c)
        for mid, result in [(1, "draw"), (2, "tie"), (3, "no_result"), (4, "pending")]:
            c.exec_driver_sql(
                "UPDATE matches SET status='completed',result_type=? WHERE match_id=?",
                (result, mid),
            )
    assert all(
        r["home_wins"] + r["away_wins"] + r["unclassified_wins"] == 0
        for r in run(database)
    )


def test_same_names_and_multiple_innings_preserve_team_match_grain(database):
    with database.transaction(write=True) as c:
        setup(c)
        c.exec_driver_sql("UPDATE teams SET name='Same Name'")
        win(c, 1, 1, 90)
        win(c, 2, 2, 91)
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM innings WHERE match_id=1"
            ).scalar_one()
            >= 2
        )
    rows = run(database)
    assert len(rows) == 2 and sum(r["home_wins"] for r in rows) == 2
