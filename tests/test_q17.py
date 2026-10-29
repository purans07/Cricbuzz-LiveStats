"""Q17 toss-decision denominators, resolved outcomes and noncausal proportions."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q17_toss_decision_win_rate.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql(
        "UPDATE matches SET toss_winner_id=NULL,toss_decision=NULL,winner_team_id=NULL,result_type='pending',margin_value=NULL,margin_unit=NULL"
    )


def outcome(c, mid, decision="bat", toss=1, winner=1, result="win", status="completed"):
    c.exec_driver_sql(
        "UPDATE matches SET toss_decision=?,toss_winner_id=?,winner_team_id=?,result_type=?,status=? WHERE match_id=?",
        (decision, toss, winner, result, status, mid),
    )


def test_bat_bowl_counts_and_noninteger_percentage(database):
    with database.transaction(write=True) as c:
        isolate(c)
        outcome(c, 1)
        outcome(c, 2, winner=2)
        outcome(c, 3, "bowl", toss=2, winner=2)
        outcome(c, 4, "bowl", toss=2, winner=2)
        outcome(c, 5, "bowl", toss=2, winner=1)
    assert run(database) == [
        {
            "toss_decision": "bat",
            "eligible_matches": 2,
            "toss_winner_match_wins": 1,
            "win_percentage": 50.0,
        },
        {
            "toss_decision": "bowl",
            "eligible_matches": 3,
            "toss_winner_match_wins": 2,
            "win_percentage": 66.67,
        },
    ]


def test_draw_tie_and_no_result_stay_in_denominator(database):
    with database.transaction(write=True) as c:
        isolate(c)
        outcome(c, 1)
        for mid, result in [(2, "draw"), (3, "tie"), (4, "no_result")]:
            outcome(c, mid, winner=None, result=result)
    assert run(database)[0]["eligible_matches"] == 4
    assert run(database)[0]["toss_winner_match_wins"] == 1
    assert run(database)[0]["win_percentage"] == 25.0


def test_pending_missing_toss_and_missing_decision_are_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        outcome(c, 1, winner=None, result="pending")
        outcome(c, 2, toss=None)
        outcome(c, 3, decision=None)
    assert all(r["eligible_matches"] == 0 for r in run(database))


def test_unfinished_or_abandoned_matches_do_not_count(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid, status in [
            (1, "live"),
            (2, "scheduled"),
            (3, "abandoned"),
            (4, "unknown"),
        ]:
            outcome(c, mid, status=status)
    assert all(r["eligible_matches"] == 0 for r in run(database))


def test_empty_decision_groups_return_unknown_rate_not_zero(database):
    with database.transaction(write=True) as c:
        isolate(c)
    rows = run(database)
    assert [r["toss_decision"] for r in rows] == ["bat", "bowl"]
    assert all(
        r["eligible_matches"] == r["toss_winner_match_wins"] == 0
        and r["win_percentage"] is None
        for r in rows
    )


def test_team_identity_and_multi_innings_count_each_match_once(database):
    with database.transaction(write=True) as c:
        isolate(c)
        outcome(c, 1, toss=2, winner=2)
        outcome(c, 2, toss=2, winner=1)
        c.exec_driver_sql("UPDATE teams SET name='Same Name'")
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM innings WHERE match_id=1"
            ).scalar_one()
            >= 2
        )
    row = run(database)[0]
    assert row["eligible_matches"] == 2 and row["win_percentage"] == 50.0
