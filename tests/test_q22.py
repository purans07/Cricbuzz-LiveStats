"""Head-to-head grain, eligibility, margins and missing information."""

from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).parents[1]
PARAMS = {"window_start": "2023-10-01T00:00:00Z", "window_end": "2026-10-01T00:00:00Z"}


def run(db, venues=False, **params):
    name = "q22_head_to_head_venues.sql" if venues else "q22_head_to_head.sql"
    with db.transaction() as c:
        return [
            dict(r)
            for r in c.execute(
                text((ROOT / "sql/queries" / name).read_text()), PARAMS | params
            ).mappings()
        ]


def test_one_pair_two_team_rows_and_test_innings_not_multiplied(database):
    rows = run(database)
    assert len(rows) == 2
    assert [r["matches_played"] for r in rows] == [72, 72]
    assert [r["wins"] for r in rows] == [37, 35]
    assert sum(r["win_percentage"] for r in rows) == 100


def test_five_match_threshold_applies_to_pair(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live' WHERE match_id>5")
    assert len(run(database)) == 2
    assert sum(r["matches_played"] for r in run(database, venues=True)) == 10
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET status='live' WHERE match_id=5")
    assert run(database) == []
    assert run(database, venues=True) == []


def test_window_is_start_inclusive_end_exclusive(database):
    with database.transaction() as c:
        first = c.exec_driver_sql("SELECT MIN(starts_at) FROM matches").scalar_one()
    assert run(database, window_end=first) == []
    assert run(database, window_start=first)[0]["matches_played"] == 72


def test_units_are_separate_and_missing_margin_audited(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE matches SET winner_team_id=1,result_type='win',margin_value=NULL,margin_unit=NULL"
        )
        c.exec_driver_sql(
            "UPDATE matches SET margin_value=20,margin_unit='runs' WHERE match_id=1"
        )
        c.exec_driver_sql(
            "UPDATE matches SET margin_value=4,margin_unit='wickets' WHERE match_id=2"
        )
    row = run(database)[0]
    assert row["average_win_margin_runs"] == 20
    assert row["average_win_margin_wickets"] == 4
    assert row["run_margin_wins"] == row["wicket_margin_wins"] == 1
    assert row["wins_missing_margin"] == 70
    assert run(database)[1]["average_win_margin_runs"] is None


def test_pending_is_not_loss_and_draw_is_resolved_nonwin(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE matches SET winner_team_id=NULL,result_type='pending',margin_value=NULL,margin_unit=NULL WHERE match_id=1"
        )
    assert all(
        r["win_percentage"] is None and r["unknown_results"] == 1 for r in run(database)
    )
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET result_type='draw' WHERE match_id=1")
    assert all(r["win_percentage"] is not None for r in run(database))
    assert sum(r["wins"] for r in run(database)) == 71


def test_venue_conditions_use_innings_not_toss_and_keep_unknown(database):
    before = run(database, venues=True)
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET toss_decision='bowl'")
    assert run(database, venues=True) == before
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE matches SET venue_id=NULL WHERE match_id=1")
        c.exec_driver_sql(
            "UPDATE innings SET is_super_over=1 WHERE match_id=1 AND innings_number=1"
        )
    missing = [r for r in run(database, venues=True) if r["venue_id"] is None]
    assert len(missing) == 2
    assert all(
        r["innings_condition"] == "unknown" and r["matches_played"] == 1
        for r in missing
    )
