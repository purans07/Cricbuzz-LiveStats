"""PostgreSQL/MySQL engines, conservative SQL translation and explicit bootstrap."""

import argparse
import hashlib
import json
import re
import tempfile
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import sqlglot
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Text,
    create_engine,
    event,
    inspect,
    text,
)
from sqlalchemy.sql.elements import TextClause
from sqlglot import exp

from config import PROJECT_ROOT, load_settings
from utils.db_connection import DatabaseError


def dialect_sql(statement, dialect):
    """Translate trusted SQLite SQL, preserving bound parameters and grouping semantics."""
    tree = sqlglot.parse_one(statement, read="sqlite")
    if dialect == "mysql" and "quarter_index" in statement:
        for division in list(tree.find_all(exp.Div)):
            if isinstance(
                division.expression, exp.Literal
            ) and division.expression.this in {"3", "4"}:
                division.replace(exp.Floor(this=division.copy()))
    if dialect == "mysql":
        for cte in tree.find_all(exp.CTE):
            values = cte.this.find(exp.Values)
            if values is not None and cte.alias_column_names:
                selects = [
                    exp.select(
                        *[
                            exp.alias_(v.copy(), col)
                            for v, col in zip(
                                row.expressions, cte.alias_column_names, strict=True
                            )
                        ]
                    )
                    for row in values.expressions
                ]
                combined = selects[0]
                for following in selects[1:]:
                    combined = exp.union(combined, following, distinct=False)
                cte.set("this", combined)
    if dialect == "postgresql":
        for rounded in tree.find_all(exp.Round):
            rounded.set("this", exp.cast(rounded.this.copy(), "DECIMAL"))
        for total in tree.find_all(exp.Sum):
            if isinstance(total.this, (exp.Predicate, exp.And, exp.Or, exp.Not)):
                total.set("this", exp.cast(total.this.copy(), "INT"))
        for select in tree.find_all(exp.Select):
            aliases = {
                n.alias: n.this for n in select.expressions if isinstance(n, exp.Alias)
            }
            order = select.args.get("order")
            if order is not None:
                for ordered in order.expressions:
                    if isinstance(ordered.this, exp.Column):
                        continue
                    for column in list(ordered.find_all(exp.Column)):
                        if not column.table and column.name in aliases:
                            column.replace(aliases[column.name].copy())
    if dialect == "mysql":
        for select in tree.find_all(exp.Select):
            source = select.args.get("from_")
            if (
                source
                and isinstance(source.this, exp.Table)
                and len(select.expressions) > 1
            ):
                for projection in list(select.expressions):
                    if isinstance(projection, exp.Star):
                        projection.replace(
                            exp.Column(
                                this=exp.Star(),
                                table=exp.to_identifier(source.this.alias_or_name),
                            )
                        )
    cte_columns = {
        cte.alias_or_name: [e.alias_or_name for e in cte.this.expressions]
        for cte in tree.find_all(exp.CTE)
        if isinstance(cte.this, exp.Select)
    }
    for select in tree.find_all(exp.Select):
        if select.args.get("group") is not None:
            aliases = {t.alias_or_name: t.name for t in select.find_all(exp.Table)}
            projections = []
            for projection in select.expressions:
                if (
                    isinstance(projection, exp.Column)
                    and projection.is_star
                    and aliases.get(projection.table) in cte_columns
                ):
                    projections.extend(
                        exp.column(name, table=projection.table)
                        for name in cte_columns[aliases[projection.table]]
                    )
                else:
                    projections.append(projection)
            select.set("expressions", projections)
        group = select.args.get("group")
        if group is None:
            continue
        existing = {e.sql() for e in group.expressions}
        for projection in select.expressions:
            value = projection.this if isinstance(projection, exp.Alias) else projection
            if value.find(exp.AggFunc) or value.find(exp.Window) or value.is_star:
                continue
            if value.sql() not in existing:
                group.append("expressions", value.copy())
                existing.add(value.sql())
    result = tree.sql(dialect="postgres" if dialect == "postgresql" else "mysql")
    return re.sub(r"%\((\w+)\)s", r":\1", result)


def server_engine(settings, *, readonly):
    """Create a server engine; reader credentials must have SELECT privileges only."""
    url = settings.read_database_url if readonly else settings.database_url
    if not url:
        raise DatabaseError("Server access requires distinct writer and reader URLs.")
    engine = create_engine(
        url,
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5}
        if url.startswith("postgresql")
        else {"connect_timeout": 5, "read_timeout": 10, "write_timeout": 10},
    )
    if engine.dialect.name == "mysql":

        @event.listens_for(engine, "connect")
        def configure_mysql(dbapi, record):
            """Enable identifier quoting and retain strict server validation."""
            with dbapi.cursor() as cursor:
                cursor.execute("SET SESSION max_execution_time=2000")

    @event.listens_for(engine, "before_execute", retval=True)
    def translate(connection, clause, multiparams, params, options):
        """Translate application-owned textual SQL before dialect parameter binding."""
        if isinstance(clause, TextClause) and not options.get("native_sql"):
            clause = text(dialect_sql(clause.text, engine.dialect.name))
        return clause, multiparams, params

    return engine


@contextmanager
def server_transaction(database, *, write=False):
    """Enforce mode, readonly transactions and serialized revision-aware writes."""
    engine = database.writer if write else database.reader
    with engine.connect() as c:
        if engine.dialect.name == "postgresql":
            c.exec_driver_sql(
                "BEGIN ISOLATION LEVEL REPEATABLE READ"
                + (" READ ONLY" if not write else "")
            )
            c.exec_driver_sql("SET LOCAL statement_timeout=2000")
            c.exec_driver_sql("SET LOCAL lock_timeout=5000")
        else:
            c.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            c.exec_driver_sql("START TRANSACTION" + (" READ ONLY" if not write else ""))
        changed = [False]

        def detect(connection, cursor, statement, parameters, context, many):
            """Track successful DML without relying on SQLite total_changes."""
            if (
                re.match(r"\s*(INSERT|UPDATE|DELETE)\b", statement, re.I)
                and cursor.rowcount > 0
            ):
                changed[0] = True

        event.listen(c, "after_cursor_execute", detect)
        try:
            suffix = " FOR UPDATE" if write else ""
            state = c.exec_driver_sql(
                "SELECT mode,schema_version FROM dataset_state WHERE singleton_id=1"
                + suffix
            ).first()
            if (
                state is None
                or state[0] != database.settings.data_mode
                or state[1] != 2
            ):
                raise DatabaseError(
                    "Server dataset mode/schema does not match configuration."
                )
            if not write:
                verify_reader(c)
            yield c
            if write and changed[0]:
                c.exec_driver_sql(
                    "UPDATE dataset_state SET revision=revision+1 WHERE singleton_id=1"
                )
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            event.remove(c, "after_cursor_execute", detect)


def verify_reader(connection):
    """Reject privileged reader roles rather than trusting the URL's account name."""
    if connection.dialect.name == "postgresql":
        elevated = connection.exec_driver_sql(
            "SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname=current_user"
        ).scalar_one()
        writes = connection.exec_driver_sql(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' AND (has_table_privilege(current_user, table_schema||'.'||table_name,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')))"
        ).scalar_one()
        create = connection.exec_driver_sql(
            "SELECT has_schema_privilege(current_user,'public','CREATE') OR has_database_privilege(current_user,current_database(),'CREATE,TEMP')"
        ).scalar_one()
        if elevated or writes or create:
            raise DatabaseError(
                "Reader role must have SELECT only, without create or write privileges."
            )
    else:
        grants = [
            r[0].upper()
            for r in connection.exec_driver_sql("SHOW GRANTS FOR CURRENT_USER").all()
        ]
        if any(
            not re.match(r"GRANT (USAGE|SELECT) ON ", g) or "GRANT OPTION" in g
            for g in grants
        ):
            raise DatabaseError(
                "Reader account must have only USAGE and SELECT privileges."
            )


def initialize_server(settings, *, seed_sample=False):
    """Create schema 2 only in an empty operator-owned server database; never overwrite."""
    if not settings.database_url or settings.access_mode != "local":
        raise DatabaseError("Explicit local server initialization is required.")
    if seed_sample and settings.data_mode != "sample":
        raise ValueError("Synthetic fixtures are forbidden in live databases.")
    from database.initialize import initialize_database

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "template.db"
        initialize_database(
            replace(
                settings, database_path=path, database_url=None, read_database_url=None
            ),
            seed_sample=seed_sample,
        )
        template = create_engine("sqlite:///" + str(path))
        metadata = MetaData()
        metadata.reflect(template)
        engine = create_engine(settings.database_url, hide_parameters=True)
        try:
            if inspect(engine).get_table_names() or inspect(engine).get_view_names():
                raise DatabaseError(
                    "Target is not empty; no server objects were changed."
                )
            for table in metadata.tables.values():
                indexed = {
                    col.name
                    for constraint in table.constraints
                    if constraint.__class__.__name__
                    in {"UniqueConstraint", "PrimaryKeyConstraint"}
                    for col in constraint.columns
                }
                indexed.update(
                    col.name for index in table.indexes for col in index.columns
                )
                for column in table.columns:
                    if isinstance(column.type, Text):
                        collation = (
                            "utf8mb4_bin" if engine.dialect.name == "mysql" else None
                        )
                        column.type = (
                            String(255, collation=collation)
                            if column.name in indexed
                            or column.server_default is not None
                            else Text(collation=collation)
                        )
                for fk in table.foreign_key_constraints:
                    digest = hashlib.sha256(str(fk).encode()).hexdigest()[:12]
                    fk.name = "fk_" + table.name[:25] + "_" + digest
                    fk.use_alter = (
                        table.name == "matches"
                        and fk.referred_table.name == "match_teams"
                    )
                # MySQL requires globally distinct CHECK names.
                for index, constraint in enumerate(table.constraints):
                    if constraint.__class__.__name__ == "CheckConstraint":
                        constraint.name = f"ck_{table.name}_{index}"
            for table in metadata.tables.values():
                keys = list(table.primary_key.columns)
                if len(keys) == 1 and isinstance(keys[0].type, Integer):
                    keys[0].autoincrement = table.name != "dataset_state"
            metadata.tables["dataset_state"].c.singleton_id.autoincrement = False
            metadata.tables["dataset_state"].append_column(
                Column("schema_version", Integer, nullable=False, server_default="2")
            )
            metadata.create_all(engine)
            with template.connect() as source, engine.begin() as target:
                deferred = []
                for table in metadata.sorted_tables:
                    records = [
                        dict(r)
                        for r in source.exec_driver_sql(
                            f'SELECT * FROM "{table.name}"'
                        ).mappings()
                    ]
                    for row in records:
                        if table.name == "matches":
                            deferred.append(
                                {
                                    k: row[k]
                                    for k in [
                                        "match_id",
                                        "toss_winner_id",
                                        "toss_decision",
                                        "winner_team_id",
                                        "result_type",
                                        "margin_value",
                                        "margin_unit",
                                    ]
                                }
                            )
                            row.update(
                                toss_winner_id=None,
                                toss_decision=None,
                                winner_team_id=None,
                                result_type="pending",
                                margin_value=None,
                                margin_unit=None,
                            )
                        target.execute(table.insert(), row)
                for row in deferred:
                    mid = row.pop("match_id")
                    target.execute(
                        metadata.tables["matches"]
                        .update()
                        .where(metadata.tables["matches"].c.match_id == mid)
                        .values(**row)
                    )
                if engine.dialect.name == "postgresql":
                    for table in metadata.tables.values():
                        keys = list(table.primary_key.columns)
                        if len(keys) == 1 and isinstance(keys[0].type, Integer):
                            col = keys[0].name
                            target.execute(
                                text(
                                    'SELECT setval(pg_get_serial_sequence(:t,:c), COALESCE((SELECT MAX("'
                                    + col
                                    + '") FROM "'
                                    + table.name
                                    + '"),0)+1,false)'
                                ),
                                {"t": table.name, "c": col},
                            )
                from database.initialize import _statements

                for statement in _statements(
                    (PROJECT_ROOT / "sql/views.sql").read_text()
                ):
                    target.exec_driver_sql(dialect_sql(statement, engine.dialect.name))
        finally:
            engine.dispose()
            template.dispose()


def main():
    """Initialize an empty server target configured privately in environment settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-sample", action="store_true")
    args = parser.parse_args()
    try:
        initialize_server(load_settings(), seed_sample=args.seed_sample)
    except Exception:
        parser.exit(
            1,
            "Server initialization failed; inspect target emptiness, privileges and logs privately.\n",
        )
    print(
        json.dumps(
            {"initialized": True, "schema_version": 2, "synthetic": args.seed_sample}
        )
    )


def validate_read(sql, allowed_tables, safe_functions):
    """Require one SELECT tree with local tables and a small pure-function allowlist."""
    try:
        trees = sqlglot.parse(sql, read="sqlite")
        if len(trees) != 1 or not isinstance(
            trees[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)
        ):
            raise ValueError
        tree = trees[0]
        if any(
            tree.find(kind)
            for kind in (
                exp.Into,
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Create,
                exp.Drop,
                exp.Command,
                exp.Lock,
                exp.Parameter,
            )
        ):
            raise ValueError
        ctes = {node.alias_or_name for node in tree.find_all(exp.CTE)}
        for table in tree.find_all(exp.Table):
            if table.db or table.catalog or table.name not in allowed_tables | ctes:
                raise ValueError
        for fn in tree.find_all(exp.Func):
            name = (
                fn.name.lower()
                if isinstance(fn, exp.Anonymous)
                else fn.sql_name().lower()
            )
            if name not in safe_functions | {
                "and",
                "or",
                "exists",
                "case",
                "row_number",
                "substring",
                "cast",
                "if",
                "least",
                "greatest",
                "time_to_str",
                "ts_or_ds_to_timestamp",
            }:
                raise ValueError
        return tree
    except (sqlglot.errors.ParseError, ValueError, TypeError):
        raise ValueError(
            "Only one bounded read using known tables and approved functions is permitted."
        ) from None


if __name__ == "__main__":
    main()
