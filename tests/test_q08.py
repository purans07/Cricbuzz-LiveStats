"""Q08 calendar boundaries, multi-valued metadata and planned-match semantics."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q08_series_started_2024.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c):
    c.exec_driver_sql("UPDATE series SET start_date='2020-01-01'")


def test_calendar_boundaries_and_unknown_dates(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for sid, start in [
            (901, "2023-12-31"),
            (902, "2024-01-01"),
            (903, "2024-12-31"),
            (904, "2025-01-01"),
            (905, None),
        ]:
            c.exec_driver_sql(
                "INSERT INTO series(series_id,name,start_date) VALUES(?,?,?)",
                (sid, f"Boundary {sid}", start),
            )
    assert [r["series_name"] for r in run(database)] == ["Boundary 902", "Boundary 903"]


def test_multiple_hosts_and_formats_return_one_series_without_cross_product(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "INSERT INTO series(series_id,name,start_date,planned_matches) VALUES(906,'Multi-host mixed-format', '2024-06-01',7)"
        )
        c.exec_driver_sql("INSERT INTO series_hosts VALUES(906,1),(906,2)")
        c.exec_driver_sql("INSERT INTO series_formats VALUES(906,1),(906,2)")
    assert run(database) == [
        {
            "series_name": "Multi-host mixed-format",
            "host_country": "Australia, India",
            "match_type": "ODI, TEST",
            "start_date": "2024-06-01",
            "total_matches_planned": 7,
        }
    ]


def test_missing_metadata_is_not_invented_from_imported_matches(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "INSERT INTO series(series_id,name,start_date) VALUES(907,'Unknown metadata','2024-07-01')"
        )
        c.exec_driver_sql("UPDATE matches SET series_id=907 WHERE match_id IN(1,2)")
    row = run(database)[0]
    assert row["host_country"] is None and row["match_type"] is None
    assert row["total_matches_planned"] is None


def test_same_names_keep_distinct_series_and_zero_is_known(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "INSERT INTO series(series_id,name,start_date,planned_matches) VALUES(908,'Same Name','2024-08-01',0),(909,'Same Name','2024-08-01',5)"
        )
    assert [r["total_matches_planned"] for r in run(database)] == [0, 5]


def test_series_overlapping_2024_but_starting_2023_is_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "INSERT INTO series(name,start_date,end_date) VALUES('Earlier start','2023-12-20','2024-01-10')"
        )
    assert run(database) == []
