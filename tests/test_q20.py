"""Q20 career format pivots, minimum totals and T20 overlap protection."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q20_format_matches_and_averages.sql"
).read_text()
SOURCE = "Synthetic training fixture"


def run(db, source=SOURCE):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"source_name": source}).mappings()
        ]


def isolate(c):
    c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id<>1")
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET matches_played=0 WHERE batch_id=2"
    )


def career(c, fid, matches, runs=100, dismissals=2, reported=None, pid=1):
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET matches_played=?,runs=?,dismissals=?,reported_batting_average=? WHERE player_id=? AND format_id=? AND batch_id=2",
        (matches, runs, dismissals, reported, pid, fid),
    )


def test_nineteen_excluded_twenty_included_with_correct_pivot(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 10, 100, 2)
        career(c, 2, 9, 180, 6)
        career(c, 3, 0, 0, 0)
    assert run(database) == []
    with database.transaction(write=True) as c:
        career(c, 3, 1, 40, 2)
    row = run(database)[0]
    assert row["total_known_matches"] == 20
    assert [row["test_matches"], row["odi_matches"], row["t20_matches"]] == [10, 9, 1]
    assert [
        row["test_batting_average"],
        row["odi_batting_average"],
        row["t20_batting_average"],
    ] == [50.0, 30.0, 20.0]


def test_latest_snapshots_and_source_isolation(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 20)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET matches_played=999 WHERE batch_id=1"
        )
        c.exec_driver_sql(
            "INSERT INTO import_batches(batch_id,source_id,capability,fetched_at,completeness,status) VALUES(97,2,'test','2026-10-03T00:00:00Z','partial','committed')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,matches_played) VALUES(1,1,97,555)"
        )
    assert run(database)[0]["total_known_matches"] == 20
    assert run(database, "Local operator")[0]["total_known_matches"] == 555
    assert run(database, "' OR 1=1 --") == []


def test_unknown_counts_reject_unstated_total_and_known_zero_stays_zero(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 20)
        career(c, 2, 0, 0, 0)
        career(c, 3, 0, 0, 0)
    row = run(database)[0]
    assert row["odi_matches"] == row["t20_matches"] == 0
    assert row["odi_batting_average"] is None
    with database.transaction(write=True) as c:
        career(c, 2, None)
    assert run(database) == []


def test_missing_or_domestic_t20_bucket_is_not_fabricated_as_zero(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 20)
        career(c, 3, 999)
        c.exec_driver_sql(
            "UPDATE formats SET code='IPL',level='domestic' WHERE format_id=3"
        )
    row = run(database)[0]
    assert row["total_known_matches"] == 20 and row["t20_matches"] is None


def test_zero_dismissals_unknown_denominator_and_reported_average(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 10, 100, 0, 99)
        career(c, 2, 10, 200, None, 42.5)
        career(c, 3, 10, 150, 3, 1)
    row = run(database)[0]
    assert row["test_batting_average"] is None
    assert row["odi_batting_average"] == 42.5
    assert row["t20_batting_average"] == 50.0


def test_overlapping_t20_buckets_are_not_added_or_arbitrarily_chosen(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 10)
        career(c, 2, 10)
        career(c, 3, 5)
        c.exec_driver_sql(
            "INSERT INTO formats(format_id,code,family,level) VALUES(90,'INTERNATIONAL_T20','T20','international')"
        )
        c.exec_driver_sql(
            "INSERT INTO career_stats_snapshots(player_id,format_id,batch_id,matches_played) VALUES(1,90,2,5)"
        )
    assert run(database) == []


def test_deleted_profiles_excluded_and_equal_names_remain_distinct(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 20, pid=1)
        career(c, 1, 20, pid=2)
        c.exec_driver_sql(
            "UPDATE players SET is_deleted=0,full_name='Same Name' WHERE player_id IN(1,2)"
        )
    assert len(run(database)) == 2
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=1")
    assert len(run(database)) == 1
