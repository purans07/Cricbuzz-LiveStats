"""Adjacent-pair history, strict thresholds, missing data and stable ranking."""

from pathlib import Path

from sqlalchemy import text

QUERY = (
    Path(__file__).parents[1] / "sql/queries/q24_successful_batting_pairs.sql"
).read_text()


def run(db):
    with db.transaction() as c:
        return [dict(r) for r in c.execute(text(QUERY)).mappings()]


def isolate(c, scores):
    c.exec_driver_sql("UPDATE batting_performances SET is_deleted=1")
    for mid, score in enumerate(scores, 1):
        for pid, value in [(1, 0), (2, score)]:
            iid = c.exec_driver_sql(
                "SELECT MIN(innings_id) FROM batting_performances WHERE player_id=? AND match_id=?",
                (pid, mid),
            ).scalar_one()
            c.exec_driver_sql(
                "UPDATE batting_performances SET is_deleted=0,runs=?,fours=0,sixes=0 WHERE player_id=? AND innings_id=?",
                (value, pid, iid),
            )


def test_five_appearances_and_strict_above_fifty(database):
    with database.transaction(write=True) as c:
        isolate(c, [50, 51, 100, 0, 49])
    r = run(database)[0]
    assert r["pair_appearances"] == r["known_scores"] == 5
    assert r["average_combined_runs"] == 50
    assert r["scores_above_50"] == 2
    assert r["highest_combined_runs"] == 100
    assert r["success_percentage"] == 40
    assert r["success_rank"] == 1
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE match_id=5"
        )
    assert run(database) == []


def test_unknown_score_does_not_become_zero_or_reduce_eligibility(database):
    with database.transaction(write=True) as c:
        isolate(c, [60, 60, 60, 60, None])
    r = run(database)[0]
    assert r["pair_appearances"] == 5 and r["missing_scores"] == 1
    assert r["success_rank"] is None
    assert r["coverage_status"] == "incomplete_scores"
    for key in (
        "average_combined_runs",
        "scores_above_50",
        "highest_combined_runs",
        "success_percentage",
    ):
        assert r[key] is None


def test_position_reversal_keeps_same_unordered_pair(database):
    with database.transaction(write=True) as c:
        isolate(c, [60] * 5)
        c.exec_driver_sql(
            "UPDATE batting_performances SET batting_position=NULL WHERE match_id=1 AND player_id IN(1,2)"
        )
        c.exec_driver_sql(
            "UPDATE batting_performances SET batting_position=2 WHERE match_id=1 AND player_id=1"
        )
        c.exec_driver_sql(
            "UPDATE batting_performances SET batting_position=1 WHERE match_id=1 AND player_id=2"
        )
    assert len(run(database)) == 1
    assert run(database)[0]["pair_appearances"] == 5


def test_missing_adjacent_position_cannot_be_bridged(database):
    with database.transaction(write=True) as c:
        isolate(c, [60] * 5)
        c.exec_driver_sql(
            "UPDATE batting_performances SET batting_position=11 WHERE match_id=1 AND player_id=2"
        )
    assert run(database) == []


def test_deleted_profile_and_superovers_excluded(database):
    with database.transaction(write=True) as c:
        isolate(c, [60] * 5)
        c.exec_driver_sql("UPDATE innings SET is_super_over=1 WHERE match_id=1")
    assert run(database) == []
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE innings SET is_super_over=0 WHERE match_id=1")
        c.exec_driver_sql("UPDATE players SET is_deleted=1 WHERE player_id=2")
    assert run(database) == []


def test_same_named_players_still_identified_by_id_and_dense_ties(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET full_name='Same Name'")
        c.exec_driver_sql("UPDATE batting_performances SET runs=30,fours=0,sixes=0")
    rows = run(database)
    assert len(rows) == 10
    assert all(r["success_rank"] == 1 for r in rows)
    assert len({(r["player_a_id"], r["player_b_id"]) for r in rows}) == 10


def test_success_rate_precedes_mean(database):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE batting_performances SET runs=0,fours=0,sixes=0")
        c.exec_driver_sql(
            "UPDATE batting_performances SET runs=30 WHERE player_id IN(1,2)"
        )
        # Pair 1/2 always has 60; pair 2/3 always has 30, despite a huge outlier.
        c.exec_driver_sql(
            "UPDATE batting_performances SET runs=10000 WHERE player_id=3 AND match_id=1"
        )
    rows = run(database)
    a = next(r for r in rows if (r["player_a_id"], r["player_b_id"]) == (1, 2))
    b = next(r for r in rows if (r["player_a_id"], r["player_b_id"]) == (2, 3))
    assert a["success_rank"] < b["success_rank"]
    assert a["average_combined_runs"] < b["average_combined_runs"]


def test_different_innings_do_not_create_pairs(database):
    with database.transaction(write=True) as c:
        isolate(c, [60] * 5)
        c.exec_driver_sql(
            "UPDATE batting_performances SET is_deleted=1 WHERE match_id=1 AND player_id=2"
        )
    assert run(database) == []
