"""Q11 multi-format eligibility, pivot values and pooled batting denominators."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q11_cross_format_batting.sql"
).read_text()
SOURCE = "Synthetic training fixture"


def run(db, source=SOURCE):
    with db.transaction() as c:
        return [
            dict(r) for r in c.execute(text(QUERY), {"source_name": source}).mappings()
        ]


def isolate(c):
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET matches_played=0 WHERE batch_id=2"
    )


def career(c, pid, fid, runs, dismissals, matches=10):
    c.exec_driver_sql(
        "UPDATE career_stats_snapshots SET matches_played=?,runs=?,dismissals=? WHERE player_id=? AND format_id=? AND batch_id=2",
        (matches, runs, dismissals, pid, fid),
    )


def test_two_format_pivot_and_weighted_average_not_mean_of_averages(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 1, 100, 1)
        career(c, 1, 2, 900, 30)
    row = run(database)[0]
    assert (
        row["test_runs"] == 100 and row["odi_runs"] == 900 and row["t20i_runs"] is None
    )
    assert row["overall_batting_average"] == 32.26  # 1000/31, not (100+30)/2.
    assert len(run(database)) == 1


def test_one_format_and_zero_or_unknown_appearances_do_not_qualify(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 1, 100, 5)
        career(c, 1, 2, 200, 5, matches=0)
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET matches_played=NULL WHERE player_id=1 AND format_id=3 AND batch_id=2"
        )
    assert run(database) == []


def test_three_formats_known_zero_and_zero_total_dismissals(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for fid, runs in [(1, 0), (2, 50), (3, 60)]:
            career(c, 2, fid, runs, 0)
    row = run(database)[0]
    assert [row["test_runs"], row["odi_runs"], row["t20i_runs"]] == [0, 50, 60]
    assert row["overall_batting_average"] is None


def test_missing_statistic_prevents_partial_overall_average(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 1, 100, 5)
        career(c, 1, 2, None, 5)
        career(c, 2, 1, 200, None)
        career(c, 2, 2, 300, 5)
    rows = run(database)
    assert len(rows) == 2
    assert all(r["overall_batting_average"] is None for r in rows)
    assert rows[0]["odi_runs"] is None


def test_ambiguous_t20_and_deleted_players_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c)
        career(c, 1, 1, 100, 5)
        career(c, 1, 3, 200, 5)
        c.exec_driver_sql(
            "UPDATE formats SET code='INTERNATIONAL_T20' WHERE format_id=3"
        )
        career(c, 2, 1, 100, 5)
        career(c, 2, 2, 200, 5)
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=2")
    assert run(database) == []


def test_latest_snapshot_source_scope_and_same_name_identities(database):
    with database.transaction(write=True) as c:
        isolate(c)
        for pid in (1, 2):
            career(c, pid, 1, 100, 5)
            career(c, pid, 2, 200, 5)
        c.exec_driver_sql(
            "UPDATE players SET full_name='Same Name' WHERE player_id IN(1,2)"
        )
        c.exec_driver_sql(
            "UPDATE career_stats_snapshots SET runs=99999 WHERE batch_id=1"
        )
    rows = run(database)
    assert [r["player_id"] for r in rows] == [1, 2]
    assert all(r["test_runs"] == 100 for r in rows)
    assert run(database, "Local operator") == []
    assert run(database, "' OR 1=1 --") == []
