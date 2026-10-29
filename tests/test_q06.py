"""Q06 active player identity counts and optional role coverage."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q06_players_per_role.sql").read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def test_sample_role_counts_and_output_columns(database):
    rows = run(database)
    assert {r["playing_role"]: r["player_count"] for r in rows} == {
        "Batsman": 3,
        "Bowler": 3,
        "All-rounder": 3,
        "Wicket-keeper": 3,
    }
    assert sum(r["player_count"] for r in rows) == 12
    assert set(rows[0]) == {"playing_role", "player_count"}
    assert [r["playing_role"] for r in rows] == [
        "All-rounder",
        "Batsman",
        "Bowler",
        "Wicket-keeper",
    ]


def test_defined_role_without_players_returns_zero(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO playing_roles(name) VALUES('Fictional Unused Role')"
        )
    assert (
        next(r for r in run(database) if r["playing_role"] == "Fictional Unused Role")[
            "player_count"
        ]
        == 0
    )


def test_deleted_and_unknown_role_players_are_not_misclassified(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
        c.exec_driver_sql("UPDATE players SET role_id=NULL WHERE player_id=2")
    rows = run(database)
    assert sum(r["player_count"] for r in rows) == 10
    assert {r["playing_role"]: r["player_count"] for r in rows}["Batsman"] == 2
    assert {r["playing_role"]: r["player_count"] for r in rows}["Bowler"] == 2


def test_same_names_count_separate_players_not_appearances(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET full_name='Same Name'")
        assert c.exec_driver_sql("SELECT COUNT(*) FROM match_players").scalar_one() > 12
    assert sum(r["player_count"] for r in run(database)) == 12


def test_no_active_players_still_returns_role_catalogue(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1")
    rows = run(database)
    assert len(rows) == 4 and all(r["player_count"] == 0 for r in rows)
