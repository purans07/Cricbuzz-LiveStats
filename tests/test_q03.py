"""Q03 ranking, latest snapshots, source isolation and batting denominators."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q03_top_odi_run_scorers.sql"
).read_text()
SOURCE = "Synthetic training fixture"


def run(db, source=SOURCE):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"source_name": source}).mappings()
        ]


def test_top_ten_order_and_requested_columns(database):
    rows = run(database)
    assert len(rows) == 10
    assert [r["total_runs"] for r in rows] == sorted(
        [r["total_runs"] for r in rows], reverse=True
    )
    assert set(rows[0]) == {"player_name", "total_runs", "batting_average", "centuries"}
    with database.transaction() as c:
        expected = c.exec_driver_sql(
            "SELECT runs,dismissals,centuries FROM career_stats_snapshots WHERE player_id=12 AND format_id=2 AND batch_id=2"
        ).one()
    assert rows[0]["player_name"] == "Sample Player 12"
    assert rows[0]["total_runs"] == expected.runs
    assert rows[0]["batting_average"] == round(expected.runs / expected.dismissals, 2)
    assert rows[0]["centuries"] == expected.centuries


def test_latest_snapshot_not_largest_and_failed_batches_excluded(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=999999 WHERE player_id=1 AND format_id=2 AND batch_id=1"
        )
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(90,1,'test','2026-10-02T00:00:00Z','partial','failed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,runs) VALUES(1,2,90,888888)"
        )
    assert all(r["total_runs"] < 888888 for r in run(database))


def test_unknown_zero_dismissals_and_reported_fallback(database):
    with database.transaction(write=True) as c:
        for pid in (1, 2, 3, 4):
            c.exec_driver_sql(
                "UPDATE career_stats_snapshots SET runs=10000 WHERE player_id=? AND format_id=2 AND batch_id=2",
                (pid,),
            )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=0,reported_batting_average=99 WHERE player_id=1 AND format_id=2 AND batch_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=NULL,reported_batting_average=42.75 WHERE player_id=2 AND format_id=2 AND batch_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=NULL,reported_batting_average=NULL,centuries=NULL WHERE player_id=3 AND format_id=2 AND batch_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET dismissals=3,reported_batting_average=1 WHERE player_id=4 AND format_id=2 AND batch_id=2"
        )
    rows = run(database)
    assert [r["player_name"] for r in rows[:4]] == [
        f"Sample Player {p:02}" for p in (1, 2, 3, 4)
    ]
    assert [r["batting_average"] for r in rows[:4]] == [None, 42.75, None, 3333.33]
    assert rows[2]["centuries"] is None


def test_deleted_and_unknown_runs_excluded_without_using_older_total(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=12")
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=NULL WHERE player_id=11 AND format_id=2 AND batch_id=2"
        )
    names = {r["player_name"] for r in run(database)}
    assert "Sample Player 12" not in names and "Sample Player 11" not in names
    assert len(names) == 10


def test_source_isolation_and_odi_only(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(91,2,'test','2026-10-03T00:00:00Z','partial','committed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,runs,dismissals) VALUES(1,2,91,777777,1)"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=999999 WHERE format_id=1"
        )
    assert all(r["total_runs"] < 777777 for r in run(database))
    assert run(database, "Local operator")[0]["total_runs"] == 777777
    assert run(database, "Missing source") == []
    assert run(database, "' OR 1=1 --") == []


def test_same_fetch_time_latest_batch_tiebreak_and_equal_names(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(92,1,'test','2026-10-01T00:00:00Z','partial','committed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,runs,dismissals,centuries) VALUES(1,2,92,22222,10,2),(2,2,92,22222,10,3)"
        )
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name' WHERE player_id IN (1,2)"
        )
    rows = run(database)
    assert [r["player_name"] for r in rows[:2]] == ["Same Name", "Same Name"]
    assert [r["total_runs"] for r in rows[:2]] == [22222, 22222]
    assert [r["centuries"] for r in rows[:2]] == [2, 3]
