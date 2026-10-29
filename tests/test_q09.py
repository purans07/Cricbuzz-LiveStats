"""Q09 strict AND thresholds, role evidence, format grain and source scope."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q09_qualified_all_rounders.sql"
).read_text()
SOURCE = "Synthetic training fixture"


def run(db, source=SOURCE):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"source_name": source}).mappings()
        ]


def isolate(c):
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET runs=0,wickets=0 WHERE batch_id=2"
    )


def score(c, pid, fid, runs, wickets):
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET runs=?,wickets=? WHERE player_id=? AND format_id=? AND batch_id=2",
        (runs, wickets, pid, fid),
    )


def test_strict_and_thresholds_same_format(database):
    with database.transaction(write=True) as c:
        isolate(c)
        score(c, 3, 1, 1000, 51)
        score(c, 3, 2, 1001, 50)
        score(c, 3, 3, 1001, 51)
    assert run(database) == [
        {
            "player_name": "Sample Player 03",
            "total_runs": 1001,
            "total_wickets": 51,
            "cricket_format": "T20I",
        }
    ]


def test_not_combined_across_formats_and_one_row_per_eligible_format(database):
    with database.transaction(write=True) as c:
        isolate(c)
        score(c, 3, 1, 2000, 0)
        score(c, 3, 2, 0, 100)
        score(c, 7, 1, 2001, 51)
        score(c, 7, 2, 2002, 52)
    rows = run(database)
    assert [r["cricket_format"] for r in rows] == ["ODI", "TEST"]
    assert all(r["player_name"] == "Sample Player 07" for r in rows)


def test_role_is_required_and_deleted_or_unknown_statistics_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        score(c, 1, 1, 5000, 100)
        score(c, 3, 1, 5000, 100)
        score(c, 7, 1, None, 100)
        score(c, 11, 1, 5000, None)
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=3")
    assert run(database) == []


def test_latest_snapshots_and_selected_source_only(database):
    with database.transaction(write=True) as c:
        isolate(c)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=99999,wickets=999 WHERE batch_id=1"
        )
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(96,2,'test','2026-10-03T00:00:00Z','partial','committed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,runs,wickets) VALUES(3,2,96,7777,77)"
        )
    assert run(database) == []
    assert run(database, "Local operator")[0]["total_runs"] == 7777
    assert run(database, "' OR 1=1 --") == []


def test_rank_ties_preserve_separate_equal_named_players(database):
    with database.transaction(write=True) as c:
        isolate(c)
        score(c, 3, 1, 2000, 60)
        score(c, 7, 1, 2000, 70)
        score(c, 11, 1, 2000, 60)
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name' WHERE player_id IN(3,7,11)"
        )
    rows = run(database)
    assert len(rows) == 3
    assert [r["total_wickets"] for r in rows] == [70, 60, 60]
