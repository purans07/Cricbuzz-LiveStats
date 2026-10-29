"""Q14 per-match overs, distinct venue matches and economy aggregation."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q14_bowling_by_venue.sql").read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql(
        "UPDATE bowling_performances SET legal_balls=0,runs_conceded=0,wickets=0,maidens=0"
    )
    c.exec_driver_sql("UPDATE matches SET venue_id=1 WHERE match_id IN(1,2,3,4)")


def figures(c, mid, balls=24, runs=24, wickets=1):
    inning = c.exec_driver_sql(
        "SELECT innings_id FROM bowling_performances WHERE player_id=7 AND match_id=? ORDER BY innings_id LIMIT 1",
        (mid,),
    ).scalar_one()
    c.exec_driver_sql(
        "UPDATE bowling_performances SET legal_balls=?,runs_conceded=?,wickets=? WHERE player_id=7 AND innings_id=?",
        (balls, runs, wickets, inning),
    )


def test_three_matches_threshold_and_arithmetic_mean_not_pooled_economy(database):
    with database.transaction(write=True) as c:
        isolate(c)
        figures(c, 1, 24, 12, 1)  # Economy 3.
        figures(c, 2, 24, 24, 2)  # Economy 6.
        figures(c, 3, 48, 72, 3)  # Economy 9.
    row = run(database)[0]
    assert row["average_economy_rate"] == 6.0  # Not pooled 6.75.
    assert row["total_wickets"] == 6 and row["matches_played"] == 3
    assert len(run(database)) == 1


def test_twenty_three_balls_excluded_but_fourth_short_match_does_not_disqualify(
    database,
):
    with database.transaction(write=True) as c:
        isolate(c)
        figures(c, 1)
        figures(c, 2)
        figures(c, 3, 23, 100, 9)
    assert run(database) == []
    with database.transaction(write=True) as c:
        figures(c, 4)
    row = run(database)[0]
    assert row["matches_played"] == 3 and row["total_wickets"] == 3


def test_two_innings_sum_to_four_overs_but_count_as_one_match(database):
    with database.transaction(write=True) as c:
        isolate(c)
        figures(c, 1, 12, 6, 1)
        number = c.exec_driver_sql(
            "SELECT MAX(innings_number)+1 FROM innings WHERE match_id=1"
        ).scalar_one()
        result = c.exec_driver_sql(
            "INSERT INTO innings(match_id,innings_number,batting_team_id,bowling_team_id) VALUES(1,?,1,2)",
            (number,),
        )
        c.exec_driver_sql(
            "INSERT INTO bowling_performances(innings_id,player_id,match_id,team_id,legal_balls,runs_conceded,wickets,updated_at) VALUES(?,7,1,2,12,12,1,'2026-10-01T00:00:00Z')",
            (result.lastrowid,),
        )
        figures(c, 2)
    assert run(database) == []  # Three innings still only two matches.
    with database.transaction(write=True) as c:
        figures(c, 3)
    row = run(database)[0]
    assert row["matches_played"] == 3 and row["total_wickets"] == 4
    assert row["average_economy_rate"] == 5.5  # Mean of 4.5, 6, 6.


def test_venue_identity_separates_counts_and_unknown_venue_is_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in (1, 2, 3):
            figures(c, mid)
        c.exec_driver_sql(
            "UPDATE venues SET name='Same Venue Name' WHERE venue_id IN(1,2)"
        )
        c.exec_driver_sql("UPDATE matches SET venue_id=2 WHERE match_id=3")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET venue_id=NULL WHERE match_id=3")
    assert run(database) == []


def test_null_statistics_do_not_create_partial_averages_or_totals(database):
    with database.transaction(write=True) as c:
        isolate(c)
        figures(c, 1, 24, None, 1)
        figures(c, 2, 24, 24, None)
        figures(c, 3)
    row = run(database)[0]
    assert row["matches_played"] == 3
    assert row["average_economy_rate"] is None and row["total_wickets"] is None
    with database.transaction(write=True) as c:
        figures(c, 1, None, 24, 1)
    assert run(database) == []


def test_deleted_bowling_players_and_superovers_do_not_establish_eligibility(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid in (1, 2, 3):
            figures(c, mid)
        c.exec_driver_sql(
            "UPDATE bowling_performances SET is_deleted=1 WHERE player_id=7 AND match_id=1"
        )
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE bowling_performances SET is_deleted=0 WHERE player_id=7 AND match_id=1"
        )
        c.exec_driver_sql("UPDATE innings SET is_super_over=1 WHERE match_id=1")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE innings SET is_super_over=0 WHERE match_id=1")
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=7")
    assert run(database) == []
