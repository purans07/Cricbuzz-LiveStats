"""Question 1 boundary behavior; fixtures are explicitly fictional."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q01_india_players.sql").read_text()


def query(database, date="2026-10-01"):
    with database.transaction() as c:
        return [
            dict(row) for row in c.execute(text(QUERY), {"as_of_date": date}).mappings()
        ]


def test_sample_result_has_only_six_india_players(database):
    rows = query(database)
    assert [r["full_name"] for r in rows] == [
        f"Sample Player {i:02}" for i in range(1, 7)
    ]
    assert set(rows[0]) == {
        "full_name",
        "playing_role",
        "batting_style",
        "bowling_style",
    }
    assert query(database, "2023-09-30") == []


def test_date_boundaries_null_role_and_soft_delete(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE player_team_memberships SET valid_to='2026-10-01' WHERE player_id=1"
        )
        c.exec_driver_sql(
            "UPDATE player_team_memberships SET valid_from='2026-10-02' WHERE player_id=2"
        )
        c.exec_driver_sql(
            "UPDATE players SET role_id=NULL,bowling_style=NULL WHERE player_id=3"
        )
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=4")
    rows = query(database)
    assert [r["full_name"] for r in rows] == [
        "Sample Player 01",
        "Sample Player 03",
        "Sample Player 05",
        "Sample Player 06",
    ]
    assert rows[1]["playing_role"] is None and rows[1]["bowling_style"] is None
    tomorrow = {r["full_name"] for r in query(database, "2026-10-02")}
    assert "Sample Player 01" not in tomorrow and "Sample Player 02" in tomorrow


def test_domestic_membership_does_not_imply_india_representation(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO teams(team_id,name,country_id,is_international) VALUES(30,'Fictional Domestic Club',1,0)"
        )
        c.exec_driver_sql(
            "UPDATE player_team_memberships SET team_id=30 WHERE player_id=7"
        )
    assert "Sample Player 07" not in {r["full_name"] for r in query(database)}


def test_multiple_memberships_deduplicate_without_collapsing_people(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO teams(team_id,name,country_id,is_international) VALUES(31,'Fictional Second India Side',1,1)"
        )
        c.exec_driver_sql(
            "INSERT INTO player_team_memberships(player_id,team_id,valid_from) VALUES(1,31,'2025-01-01')"
        )
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name',role_id=NULL,batting_style=NULL,bowling_style=NULL WHERE player_id IN (1,2)"
        )
    rows = query(database)
    assert len(rows) == 6
    assert sum(r["full_name"] == "Same Name" for r in rows) == 2
