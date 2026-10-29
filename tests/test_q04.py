"""Q04 strict capacity boundary, unknown location, and venue identity."""

from pathlib import Path

from sqlalchemy import text

QUERY = (Path(__file__).parents[1] / "sql/queries/q04_large_venues.sql").read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def test_strict_capacity_boundary_and_unknowns(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE venues SET capacity=NULL")
        for name, capacity in [
            ("Below", 49999),
            ("Exactly", 50000),
            ("Above", 50001),
            ("Unknown", None),
        ]:
            c.exec_driver_sql(
                "INSERT INTO venues(name,capacity) VALUES(?,?)", (name, capacity)
            )
    assert run(database) == [
        {"venue_name": "Above", "city": None, "country": None, "capacity": 50001}
    ]


def test_country_join_and_descending_capacity(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE venues SET capacity=NULL")
        c.exec_driver_sql(
            "INSERT INTO venues(name,city,country_id,capacity) VALUES('Smaller','City A',1,60000),('Larger','City B',2,90000)"
        )
    rows = run(database)
    assert [r["venue_name"] for r in rows] == ["Larger", "Smaller"]
    assert [r["country"] for r in rows] == ["Australia", "India"]
    assert set(rows[0]) == {"venue_name", "city", "country", "capacity"}


def test_equal_capacities_and_names_retain_distinct_venues(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE venues SET capacity=NULL")
        c.exec_driver_sql(
            "INSERT INTO venues(name,city,capacity) VALUES('Same Name','First City',70000),('Same Name','Second City',70000)"
        )
    rows = run(database)
    assert len(rows) == 2
    assert [r["city"] for r in rows] == ["First City", "Second City"]


def test_no_qualifying_capacity_returns_empty(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE venues SET capacity=50000")
    assert run(database) == []
