"""Q10 match grain, nullable outcomes, result units and chronological policy."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q10_last_completed_matches.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def reset(c):
    c.exec_driver_sql("UPDATE matches SET completed_at=NULL")


def test_twenty_match_limit_and_completion_order(database):
    with database.transaction(write=True) as c:
        reset(c)
        for mid in range(1, 26):
            c.exec_driver_sql(
                "UPDATE matches SET completed_at=?,description=? WHERE match_id=?",
                (f"2026-10-{mid:02}T12:00:00Z", f"Finished {mid}", mid),
            )
    rows = run(database)
    assert len(rows) == 20
    assert [r["match_description"] for r in rows] == [
        f"Finished {mid}" for mid in range(25, 5, -1)
    ]
    assert set(rows[0]) == {
        "match_description",
        "team1_name",
        "team2_name",
        "winning_team",
        "victory_margin",
        "victory_type",
        "venue_name",
    }


def test_only_completed_status_qualifies(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live'")
        for mid, status in [
            (1, "scheduled"),
            (2, "abandoned"),
            (3, "unknown"),
            (4, "completed"),
        ]:
            c.exec_driver_sql(
                "UPDATE matches SET status=?,description=? WHERE match_id=?",
                (status, f"Status {mid}", mid),
            )
    assert [r["match_description"] for r in run(database)] == ["Status 4"]


def test_nonwinning_and_unresolved_results_are_retained(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live'")
        for mid, result in [(1, "draw"), (2, "tie"), (3, "no_result"), (4, "pending")]:
            c.exec_driver_sql(
                "UPDATE matches SET status='completed',winner_team_id=NULL,result_type=?,margin_value=NULL,margin_unit=NULL WHERE match_id=?",
                (result, mid),
            )
    rows = run(database)
    assert len(rows) == 4
    assert all(
        r["winning_team"] is None
        and r["victory_margin"] is None
        and r["victory_type"] is None
        for r in rows
    )


def test_team_slots_typed_margins_and_optional_venue(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live'")
        for mid, team, amount, unit in [(1, 1, 25, "runs"), (2, 2, 3, "wickets")]:
            c.exec_driver_sql(
                "UPDATE matches SET status='completed',description=?,winner_team_id=?,result_type='win',margin_value=?,margin_unit=?,venue_id=NULL WHERE match_id=?",
                (f"Result {mid}", team, amount, unit, mid),
            )
        expected = {
            row[0]: row[1]
            for row in c.exec_driver_sql("SELECT team_id,name FROM teams")
        }
    rows = {r["match_description"]: r for r in run(database)}
    assert rows["Result 1"]["winning_team"] == expected[1]
    assert rows["Result 2"]["winning_team"] == expected[2]
    assert (rows["Result 1"]["victory_margin"], rows["Result 1"]["victory_type"]) == (
        25,
        "runs",
    )
    assert (rows["Result 2"]["victory_margin"], rows["Result 2"]["victory_type"]) == (
        3,
        "wickets",
    )
    assert all(r["venue_name"] is None for r in rows.values())
    assert rows["Result 1"]["team1_name"] == expected[1]
    assert rows["Result 1"]["team2_name"] == expected[2]


def test_completion_precedes_start_order_and_unknown_times_remain(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live'")
        for mid, start, end in [
            (1, "2026-10-01T00:00:00Z", "2026-10-05T00:00:00Z"),
            (2, "2026-10-02T00:00:00Z", "2026-10-04T00:00:00Z"),
            (3, "2026-10-20T00:00:00Z", None),
        ]:
            c.exec_driver_sql(
                "UPDATE matches SET status='completed',description=?,starts_at=?,completed_at=? WHERE match_id=?",
                (f"Time {mid}", start, end, mid),
            )
    assert [r["match_description"] for r in run(database)] == [
        "Time 1",
        "Time 2",
        "Time 3",
    ]


def test_multiple_innings_and_date_ties_do_not_duplicate_matches(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live'")
        c.exec_driver_sql(
            "UPDATE matches SET status='completed',starts_at='2026-10-01T00:00:00Z',completed_at='2026-10-05T00:00:00Z',description='Match ' || match_id WHERE match_id IN(1,2)"
        )
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM innings WHERE match_id=1"
            ).scalar_one()
            >= 2
        )
    assert [r["match_description"] for r in run(database)] == ["Match 2", "Match 1"]
