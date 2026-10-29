"""Q07 maxima across latest career scores and verified format scopes."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q07_highest_score_per_format.sql"
).read_text()
SOURCE = "Synthetic training fixture"


def run(db, source=SOURCE):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"source_name": source}).mappings()
        ]


def test_individual_maximum_not_sum_and_requested_format_order(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET highest_score=10 WHERE batch_id=2"
        )
        for fid, score in [(1, 250), (2, 175), (3, 101)]:
            c.exec_driver_sql(
                "UPDATE career_stats_snapshots SET highest_score=? WHERE player_id=1 AND format_id=? AND batch_id=2",
                (score, fid),
            )
    assert run(database) == [
        {"format": "Test", "highest_score": 250},
        {"format": "ODI", "highest_score": 175},
        {"format": "T20I", "highest_score": 101},
    ]


def test_latest_snapshots_and_deleted_players(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET highest_score=9999 WHERE batch_id=1"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET highest_score=8888 WHERE player_id=1 AND batch_id=2"
        )
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert all(r["highest_score"] < 8888 for r in run(database))


def test_unknown_highest_scores_remain_null_not_zero(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET highest_score=NULL WHERE format_id=2 AND batch_id=2"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET highest_score=0 WHERE format_id=3 AND batch_id=2"
        )
    rows = run(database)
    assert rows[1] == {"format": "ODI", "highest_score": None}
    assert rows[2] == {"format": "T20I", "highest_score": 0}


def test_missing_format_keeps_requested_row_and_ambiguous_t20_excluded(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE formats SET code='INTERNATIONAL_T20' WHERE code='T20I'"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET highest_score=9999 WHERE format_id=3"
        )
    assert run(database)[2] == {"format": "T20I", "highest_score": None}


def test_source_isolation_and_bound_source_name(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(95,2,'test','2026-10-03T00:00:00Z','partial','committed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,highest_score) VALUES(1,2,95,9999)"
        )
    assert run(database)[1]["highest_score"] != 9999
    assert run(database, "Local operator")[1]["highest_score"] == 9999
    assert all(r["highest_score"] is None for r in run(database, "' OR 1=1 --"))
