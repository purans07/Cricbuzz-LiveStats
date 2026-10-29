"""Q02 time boundaries, actual play, joins, and result grain."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q02_recent_matches.sql").read_text()
PARAMS = {"window_start": "2026-09-01T00:00:00Z", "as_of_utc": "2026-10-01T00:00:00Z"}


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY), PARAMS).mappings()]


def isolate(c):
    c.exec_driver_sql("UPDATE matches SET starts_at='2020-01-01T00:00:00Z'")


def test_inclusive_30_day_boundaries_and_future_exclusion(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid, stamp in [
            (1, "2026-09-01T00:00:00Z"),
            (2, "2026-08-31T23:59:59Z"),
            (3, "2026-10-01T00:00:00Z"),
            (4, "2026-10-01T00:00:01Z"),
        ]:
            c.exec_driver_sql(
                "UPDATE matches SET starts_at=?,description=? WHERE match_id=?",
                (stamp, f"Boundary {mid}", mid),
            )
    rows = run(database)
    assert [r["match_description"] for r in rows] == ["Boundary 3", "Boundary 1"]
    assert set(rows[0]) == {
        "match_description",
        "team1_name",
        "team2_name",
        "venue_name",
        "venue_city",
        "match_date",
    }


def test_two_team_slots_and_missing_venue_do_not_drop_match(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "UPDATE matches SET starts_at='2026-09-10T00:00:00Z',venue_id=NULL WHERE match_id=1"
        )
        expected = [
            r[0]
            for r in c.exec_driver_sql(
                "SELECT t.name FROM match_teams mt JOIN teams t ON t.team_id=mt.team_id WHERE mt.match_id=1 ORDER BY mt.slot"
            )
        ]
    row = run(database)[0]
    assert [row["team1_name"], row["team2_name"]] == expected
    assert row["venue_name"] is None and row["venue_city"] is None


def test_play_status_and_balls_evidence(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for mid, status in [
            (1, "scheduled"),
            (2, "unknown"),
            (3, "live"),
            (4, "live"),
            (5, "abandoned"),
            (6, "abandoned"),
            (7, "completed"),
        ]:
            c.exec_driver_sql(
                "UPDATE matches SET starts_at='2026-09-10T00:00:00Z',status=?,description=? WHERE match_id=?",
                (status, f"Status {mid}", mid),
            )
        c.exec_driver_sql("UPDATE innings SET legal_balls=0 WHERE match_id IN(3,5,7)")
    assert [r["match_description"] for r in run(database)] == [
        "Status 7",
        "Status 6",
        "Status 4",
    ]


def test_multiple_innings_remain_one_row_and_null_dates_are_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "UPDATE matches SET starts_at='2026-09-10T00:00:00Z' WHERE match_id=1"
        )
        c.exec_driver_sql("UPDATE matches SET starts_at=NULL WHERE match_id=2")
        assert (
            c.exec_driver_sql(
                "SELECT COUNT(*) FROM innings WHERE match_id=1"
            ).scalar_one()
            >= 2
        )
    assert len(run(database)) == 1
