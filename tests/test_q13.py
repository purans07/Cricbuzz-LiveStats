"""Q13 adjacent positions, single-innings grain, thresholds and active views."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q13_adjacent_batting_pairs.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql("UPDATE batting_performances SET runs=0,fours=0,sixes=0")


def runs(c, pid, value, inning=11):
    result = c.exec_driver_sql(
        "UPDATE batting_performances SET runs=? WHERE player_id=? AND innings_id=?",
        (value, pid, inning),
    )
    assert result.rowcount == 1


def test_exact_hundred_qualifies_but_ninety_nine_does_not(database):
    with database.transaction(write=True) as c:
        isolate(c)
        runs(c, 1, 40)
        runs(c, 2, 60)
    row = run(database)[0]
    assert row == {
        "match_id": 1,
        "innings_id": 11,
        "innings_number": 1,
        "player1_name": "Sample Player 01",
        "player2_name": "Sample Player 02",
        "combined_runs": 100,
    }
    assert len(run(database)) == 1
    with database.transaction(write=True) as c:
        runs(c, 2, 59)
    assert run(database) == []


def test_overlapping_adjacent_pairs_once_each_not_all_combinations(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for pid in (1, 2, 3):
            runs(c, pid, 60)
    rows = run(database)
    assert [(r["player1_name"], r["player2_name"]) for r in rows] == [
        ("Sample Player 01", "Sample Player 02"),
        ("Sample Player 02", "Sample Player 03"),
    ]
    assert all(r["combined_runs"] == 120 for r in rows)


def test_different_innings_cannot_be_combined(database):
    with database.transaction(write=True) as c:
        isolate(c)
        runs(c, 1, 60)
        other = c.exec_driver_sql(
            "SELECT innings_id FROM batting_performances WHERE player_id=2 AND innings_id<>11 ORDER BY innings_id LIMIT 1"
        ).scalar_one()
        runs(c, 2, 60, other)
    assert run(database) == []


def test_deleted_gap_is_not_skipped_and_deleted_players_and_superovers_excluded(
    database,
):
    with database.transaction(write=True) as c:
        isolate(c)
        for pid, value in [(1, 60), (2, 40), (3, 60)]:
            runs(c, pid, value)
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE innings_id=11 AND player_id=2"
        )
    assert run(database) == []  # Positions 1 and 3 must not become adjacent.
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=0 WHERE innings_id=11 AND player_id=2"
        )
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=2")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=0 WHERE player_id=2")
        c.exec_driver_sql("UPDATE innings SET is_super_over=1 WHERE innings_id=11")
    assert run(database) == []


def test_unknown_runs_and_unknown_position_do_not_create_pair(database):
    with database.transaction(write=True) as c:
        isolate(c)
        runs(c, 1, 60)
        runs(c, 2, None)
    assert run(database) == []
    with database.transaction(write=True) as c:
        runs(c, 2, 60)
        c.exec_driver_sql(
            "UPDATE batting_performances SET batting_position=NULL WHERE innings_id=11 AND player_id=2"
        )
    assert run(database) == []


def test_equal_names_do_not_merge_identities_or_reverse_pair(database):
    with database.transaction(write=True) as c:
        isolate(c)
        runs(c, 1, 50)
        runs(c, 2, 50)
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name' WHERE player_id IN(1,2)"
        )
    rows = run(database)
    assert len(rows) == 1
    assert rows[0]["player1_name"] == rows[0]["player2_name"] == "Same Name"
