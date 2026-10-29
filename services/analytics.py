"""Allowlisted lessons and bounded SQLite reads; custom SQL is local-only."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from time import monotonic

from config import PROJECT_ROOT
from utils.dates import validate_date


class AnalyticsError(ValueError):
    """Safe user-facing query failure without SQL, paths or private settings."""


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    filename: str
    lesson: str
    parameters: tuple[str, ...] = ()


# Explicit registry: SQL filenames and lesson paths are never supplied by visitors.
QUESTIONS = (
    Question(
        "Q01",
        "India players",
        "q01_india_players.sql",
        "11_q01_india_players.md",
        ("as_of_date",),
    ),
    Question(
        "Q02",
        "Recent matches",
        "q02_recent_matches.sql",
        "11_q02_recent_matches.md",
        ("window_start", "as_of_utc"),
    ),
    Question(
        "Q03",
        "Top odi run scorers",
        "q03_top_odi_run_scorers.sql",
        "11_q03_top_odi_run_scorers.md",
        ("source_name",),
    ),
    Question(
        "Q04", "Large venues", "q04_large_venues.sql", "11_q04_large_venues.md", ()
    ),
    Question("Q05", "Team wins", "q05_team_wins.sql", "11_q05_team_wins.md", ()),
    Question(
        "Q06",
        "Players per role",
        "q06_players_per_role.sql",
        "11_q06_players_per_role.md",
        (),
    ),
    Question(
        "Q07",
        "Highest score per format",
        "q07_highest_score_per_format.sql",
        "11_q07_highest_score_per_format.md",
        ("source_name",),
    ),
    Question(
        "Q08",
        "Series started 2024",
        "q08_series_started_2024.sql",
        "11_q08_series_started_2024.md",
        (),
    ),
    Question(
        "Q09",
        "Qualified all rounders",
        "q09_qualified_all_rounders.sql",
        "11_q09_qualified_all_rounders.md",
        ("source_name",),
    ),
    Question(
        "Q10",
        "Last completed matches",
        "q10_last_completed_matches.sql",
        "11_q10_last_completed_matches.md",
        (),
    ),
    Question(
        "Q11",
        "Cross format batting",
        "q11_cross_format_batting.sql",
        "11_q11_cross_format_batting.md",
        ("source_name",),
    ),
    Question(
        "Q12",
        "Home away wins",
        "q12_home_away_wins.sql",
        "11_q12_home_away_wins.md",
        (),
    ),
    Question(
        "Q13",
        "Adjacent batting pairs",
        "q13_adjacent_batting_pairs.sql",
        "11_q13_adjacent_batting_pairs.md",
        (),
    ),
    Question(
        "Q14",
        "Bowling by venue",
        "q14_bowling_by_venue.sql",
        "11_q14_bowling_by_venue.md",
        (),
    ),
    Question(
        "Q15",
        "Close match batting",
        "q15_close_match_batting.sql",
        "11_q15_close_match_batting.md",
        (),
    ),
    Question(
        "Q16",
        "Yearly batting",
        "q16_yearly_batting.sql",
        "11_q16_yearly_batting.md",
        (),
    ),
    Question(
        "Q17",
        "Toss decision win rate",
        "q17_toss_decision_win_rate.sql",
        "11_q17_toss_decision_win_rate.md",
        (),
    ),
    Question(
        "Q18",
        "Limited overs economy",
        "q18_limited_overs_economy.sql",
        "11_q18_limited_overs_economy.md",
        (),
    ),
    Question(
        "Q19",
        "Batting consistency",
        "q19_batting_consistency.sql",
        "11_q19_batting_consistency.md",
        (),
    ),
    Question(
        "Q20",
        "Format matches and averages",
        "q20_format_matches_and_averages.sql",
        "11_q20_format_matches_and_averages.md",
        ("source_name",),
    ),
    Question(
        "Q21",
        "Weighted performance rank",
        "q21_weighted_performance_rank.sql",
        "11_q21_weighted_performance_rank.md",
        ("source_name",),
    ),
    Question(
        "Q22",
        "Head to head",
        "q22_head_to_head.sql",
        "11_q22_head_to_head.md",
        ("window_start", "window_end"),
    ),
    Question(
        "Q23",
        "Recent player form",
        "q23_recent_player_form.sql",
        "11_q23_recent_player_form.md",
        ("as_of_utc",),
    ),
    Question(
        "Q24",
        "Successful batting pairs",
        "q24_successful_batting_pairs.sql",
        "11_q24_successful_batting_pairs.md",
        (),
    ),
    Question(
        "Q25",
        "Quarterly player evolution",
        "q25_quarterly_player_evolution.sql",
        "11_q25_quarterly_player_evolution.md",
        ("window_start", "window_end"),
    ),
    Question(
        "Q26",
        "Saved match coverage",
        "q26_match_coverage.sql",
        "11_q26_match_coverage.md",
        (),
    ),
)
REGISTRY = {q.id: q for q in QUESTIONS}
SOURCE_QUESTIONS = {q.id for q in QUESTIONS if "source_name" in q.parameters}
SAFE_FUNCTIONS = {
    "abs",
    "avg",
    "cast",
    "coalesce",
    "count",
    "date",
    "datetime",
    "dense_rank",
    "group_concat",
    "ifnull",
    "instr",
    "julianday",
    "lag",
    "lead",
    "length",
    "lower",
    "ltrim",
    "max",
    "min",
    "nullif",
    "rank",
    "replace",
    "round",
    "row_number",
    "rtrim",
    "sqrt",
    "strftime",
    "substr",
    "substring",
    "sum",
    "total",
    "trim",
    "upper",
    "typeof",
    "printf",
    "format",
}


def question(query_id):
    """Resolve a saved question through the fixed registry; reject unknown IDs."""
    try:
        return REGISTRY[query_id]
    except (KeyError, TypeError):
        raise AnalyticsError("Choose a saved question.") from None


def saved_sql(query_id, *, venue_breakdown=False):
    """Load only the SQL file allowlisted for the selected question and variant."""
    q = question(query_id)
    if venue_breakdown and q.id != "Q22":
        raise AnalyticsError("Venue breakdown is available for Q22 only.")
    filename = "q22_head_to_head_venues.sql" if venue_breakdown else q.filename
    return (PROJECT_ROOT / "sql/queries" / filename).read_text()


def parameters(query_id, analysis_date, source_name=None):
    """Generate lesson-defined calendar boundaries, never guessed SQL text."""
    q = question(query_id)
    try:
        day = date.fromisoformat(validate_date(analysis_date))
    except (ValueError, TypeError, AttributeError):
        raise AnalyticsError("Choose a valid analysis date.") from None
    if not 2000 <= day.year <= 2100:
        raise AnalyticsError("Choose an analysis date from 2000 through 2100.")
    endpoint = datetime.combine(day, datetime.min.time(), tzinfo=UTC)

    def stamp(d):
        """Return a canonical UTC timestamp for persisted metadata."""
        return d.strftime("%Y-%m-%dT%H:%M:%SZ")

    values = {"as_of_date": day.isoformat(), "as_of_utc": stamp(endpoint)}
    if q.id == "Q02":
        values["window_start"] = stamp(endpoint - timedelta(days=30))
    elif q.id == "Q22":
        try:
            start = endpoint.replace(year=endpoint.year - 3)
        except ValueError:
            start = endpoint.replace(year=endpoint.year - 3, day=28)
        values.update(window_start=stamp(start), window_end=stamp(endpoint))
    elif q.id == "Q25":
        end = endpoint.replace(month=((day.month - 1) // 3) * 3 + 1, day=1)
        try:
            start = end.replace(year=end.year - 3)
        except ValueError:
            raise AnalyticsError(
                "The analysis date is outside the supported range."
            ) from None
        values.update(window_start=stamp(start), window_end=stamp(end))
    if "source_name" in q.parameters:
        if not isinstance(source_name, str) or not source_name.strip():
            raise AnalyticsError("Select a statistics source.")
        values["source_name"] = source_name
    return {key: values[key] for key in q.parameters}


def _authorize(action, arg1, arg2, database, trigger):
    """Allow only approved SQLite read actions and functions during analysis."""
    if action in {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_RECURSIVE}:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in SAFE_FUNCTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


class AnalyticsService:
    """Execute a single statement under database-enforced read restrictions."""

    def __init__(self, database):
        """Retain validated dependencies for this component without performing its operations."""
        self.database = database

    def sources(self):
        """List committed analytical data sources without combining their records."""
        with self.database.transaction() as c:
            return list(
                c.exec_driver_sql("SELECT name FROM sources ORDER BY name").scalars()
            )

    def schema(self):
        """Return public dataset table/view definitions, not filesystem metadata."""
        if self.database.settings.database_url:
            from sqlalchemy import inspect

            with self.database.transaction() as c:
                inspector = inspect(c)
                return [
                    {"name": n, "type": k, "sql": None}
                    for k, names in [
                        ("table", inspector.get_table_names()),
                        ("view", inspector.get_view_names()),
                    ]
                    for n in names
                ]
        with self.database.transaction() as c:
            return [
                dict(r)
                for r in c.exec_driver_sql(
                    "SELECT name,type,sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type,name"
                ).mappings()
            ]

    def run_saved(
        self,
        query_id,
        analysis_date,
        source_name=None,
        *,
        venue_breakdown=False,
        row_limit=500,
    ):
        """Bind the selected lesson parameters and execute its reviewed read-only SQL."""
        sql = saved_sql(query_id, venue_breakdown=venue_breakdown)
        params = parameters(query_id, analysis_date, source_name)
        return self._read(sql, params, row_limit=row_limit)

    def run_custom(self, sql, *, row_limit=500):
        """Run bounded local-operator SQL under database read-only authorization."""
        if self.database.settings.access_mode != "local":
            raise AnalyticsError("Custom SQL is disabled in read-only visitor mode.")
        return self._read(sql, {}, row_limit=row_limit)

    def _read(self, sql, params, *, row_limit=500, seconds=2.0):
        """Execute one restricted query with cooperative time, row and result-size limits."""
        if not isinstance(sql, str) or not sql.strip() or len(sql.encode()) > 20000:
            raise AnalyticsError("Supply one query of at most 20,000 bytes.")
        if type(row_limit) is not int or not 1 <= row_limit <= 500:
            raise AnalyticsError("Choose a row limit from 1 to 500.")
        if self.database.settings.database_url:
            return self._server_read(sql, params, row_limit)
        try:
            with self.database.transaction() as c:
                revision = c.exec_driver_sql(
                    "SELECT revision FROM dataset_state WHERE singleton_id=1"
                ).scalar_one()
                driver = c.connection.driver_connection
                driver.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 200000)
                driver.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 20000)
                driver.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 100)
                driver.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 100)
                deadline = monotonic() + seconds
                driver.set_authorizer(_authorize)
                driver.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
                cursor = None
                try:
                    cursor = driver.execute(sql, params)
                    if cursor.description is None:
                        raise AnalyticsError(
                            "Only read queries returning a table are supported."
                        )
                    columns = [item[0] for item in cursor.description]
                    rows = []
                    size = 0
                    truncated = False
                    for row in cursor:
                        if len(rows) >= row_limit:
                            truncated = True
                            break
                        values = [
                            f"[binary data: {len(v)} bytes]"
                            if isinstance(v, bytes)
                            else v
                            for v in row
                        ]
                        size += len(json.dumps(values, ensure_ascii=False).encode())
                        if size > 1000000:
                            truncated = True
                            break
                        rows.append(values)
                    return {
                        "columns": columns,
                        "rows": rows,
                        "truncated": truncated,
                        "revision": revision,
                    }
                finally:
                    if cursor is not None:
                        cursor.close()
                    driver.set_progress_handler(None, 0)
                    driver.set_authorizer(None)
        except (sqlite3.Error, MemoryError, OverflowError):
            raise AnalyticsError(
                "Query could not run: use one permitted read statement, check names and syntax, or simplify an expensive query. Writes, file operations, unsupported functions and oversized results are blocked."
            ) from None

    def _server_read(self, sql, params, row_limit):
        """Execute validated reads using a SELECT-only server role and bounded output."""
        from decimal import Decimal

        from sqlalchemy import inspect, text
        from sqlalchemy.exc import SQLAlchemyError

        from database.server import validate_read

        try:
            with self.database.transaction() as c:
                inspector = inspect(c)
                allowed = set(inspector.get_table_names()) | set(
                    inspector.get_view_names()
                )
                validate_read(sql, allowed, SAFE_FUNCTIONS)
                revision = c.exec_driver_sql(
                    "SELECT revision FROM dataset_state WHERE singleton_id=1"
                ).scalar_one()
                result = c.execute(text(sql), params)
                try:
                    columns = list(result.keys())
                    if len(columns) > 100:
                        raise ValueError
                    rows, size, truncated = [], 0, False
                    for row in result:
                        if len(rows) >= row_limit:
                            truncated = True
                            break
                        values = [
                            float(v)
                            if isinstance(v, Decimal)
                            else (
                                f"[binary data: {len(v)} bytes]"
                                if isinstance(v, bytes)
                                else v
                            )
                            for v in row
                        ]
                        if any(
                            isinstance(v, str) and len(v.encode()) > 200000
                            for v in values
                        ):
                            raise ValueError
                        size += len(json.dumps(values, ensure_ascii=False).encode())
                        if size > 1000000:
                            truncated = True
                            break
                        rows.append(values)
                    return {
                        "columns": columns,
                        "rows": rows,
                        "revision": revision,
                        "truncated": truncated,
                    }
                finally:
                    result.close()
        except (SQLAlchemyError, ValueError, MemoryError, OverflowError):
            raise AnalyticsError(
                "Query could not run: use one permitted read statement, check names and syntax, or simplify an expensive query."
            ) from None
