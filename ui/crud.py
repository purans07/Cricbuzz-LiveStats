"""Version-aware administrative forms using the existing authoritative services."""

from dataclasses import replace

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from config import PROJECT_ROOT, ConfigurationError, load_settings
from database.repositories import StaleRecordError
from services.crud_catalog import CrudCatalog
from services.match_stats import FIELDS, MatchStatsService
from services.players import PlayerService
from ui.preferences import apply_preferences
from utils.db_connection import Database, DatabaseError
from utils.logging_config import log_event


def optional_integer(value):
    """Blank means unknown; never silently turn missing statistics into zero."""
    value = value.strip()
    if not value:
        return None
    if not value.isascii() or not value.isdigit():
        raise ValueError(
            "Numeric statistics must be non-negative whole numbers or blank."
        )
    return int(value)


def _fields(entity, record, roles, prefix):
    """Build statistic form controls for the selected supported record type."""
    fields = {}
    if entity == "Players":
        fields["full_name"] = st.text_input(
            "Player name", value=record.get("full_name", ""), key=prefix + "name"
        )
        options = [None, *roles]
        fields["role_id"] = st.selectbox(
            "Role",
            options,
            index=options.index(record.get("role_id"))
            if record.get("role_id") in options
            else 0,
            format_func=lambda v: roles.get(v, "Unknown"),
            key=prefix + "role",
        )
        for key, label in [
            ("batting_style", "Batting style"),
            ("bowling_style", "Bowling style"),
        ]:
            fields[key] = (
                st.text_input(
                    label, value=record.get(key) or "", key=prefix + key
                ).strip()
                or None
            )
    else:
        for key in FIELDS[entity]:
            label = (
                "Legal balls (not overs)"
                if key == "legal_balls"
                else key.replace("_", " ").capitalize()
            )
            fields[key] = st.text_input(
                label,
                value="" if record.get(key) is None else str(record[key]),
                key=prefix + key,
            )
    return fields


def _clean(entity, fields):
    """Validate supplied fields and preserve unknown values rather than inventing defaults."""
    if entity == "Players":
        fields["full_name"] = fields["full_name"].strip()
        return fields
    return {
        k: optional_integer(v) if FIELDS[entity][k] == "INTEGER" else v.strip() or None
        for k, v in fields.items()
    }


def _page(database):
    """Render the selected dataset through services while respecting its access policy."""
    catalog = CrudCatalog(database)
    entity = st.selectbox(
        "Record type", ["Players", "batting", "bowling", "fielding"], key="crud_entity"
    )
    rows = catalog.players() if entity == "Players" else catalog.records(entity)
    st.info(
        "SAMPLE DATA · Changes affect the selected fictional dataset."
        if database.settings.data_mode == "sample"
        else "PROVIDER DATA · Local corrections and deletions are protected by ownership rules."
    )
    st.caption(
        "Deletes are reversible. Deleting a player hides dependent statistics and careers from active views; it does not physically erase them. Creating a player does not add match participation or career totals."
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if database.settings.access_mode != "local":
        st.info("Read-only mode: administrative forms are unavailable.")
        return
    action = st.selectbox(
        "Action",
        ["Create", "Edit", "Delete", "Restore", "Release override"],
        key="crud_action",
    )
    context = f"{database.settings.database_path}:{entity}:{action}:{st.session_state.get('crud_generation', 0)}"
    record = {}
    identity = None
    if action != "Create":
        if not rows:
            st.info("No records are available to select.")
            return
        options = list(range(len(rows)))
        selected = st.selectbox(
            "Record",
            options,
            format_func=lambda n: (
                f"#{rows[n]['player_id']} · {rows[n].get('full_name', 'Player')}"
                + (
                    f" · innings #{rows[n]['innings_id']}"
                    if entity != "Players"
                    else ""
                )
                + (" · deleted" if rows[n]["is_deleted"] else "")
            ),
            key="crud_record",
        )
        current = rows[selected]
        identity = (current["player_id"], current.get("innings_id"))
        token = (context, identity)
        reload = st.button("Reload selected record", key="crud_reload")
        if reload or st.session_state.get("crud_token") != token:
            st.session_state["crud_token"] = token
            st.session_state["crud_snapshot"] = dict(current)
        record = dict(st.session_state["crud_snapshot"])
        st.caption(
            f"Loaded version {record['version']} · Ownership: {record['ownership']} · {'Deleted' if record['is_deleted'] else 'Active'}. Reload before retrying a stale edit."
        )
    relationship = None
    if action == "Create" and entity != "Players":
        eligible = catalog.eligible(entity)
        if not eligible:
            st.info(
                "No eligible match participants exist. Create/import match participation before adding statistics."
            )
            return
        n = st.selectbox(
            "Match / innings / player",
            list(range(len(eligible))),
            format_func=lambda n: (
                f"Match #{eligible[n]['match_id']} · innings {eligible[n]['innings_number']} · {eligible[n]['full_name']} (#{eligible[n]['player_id']})"
            ),
            key="crud_relationship",
        )
        relationship = eligible[n]
        context += f":{relationship['match_id']}:{relationship['innings_id']}:{relationship['player_id']}"
    prefix = f"{context}:{identity}:{record.get('version', 0)}:"
    with st.form("crud_form"):
        fields = (
            _fields(entity, record, catalog.roles(), prefix)
            if action in {"Create", "Edit"}
            else {}
        )
        override = (
            st.checkbox(
                "Create a local override for this API-owned record",
                key=prefix + "override",
            )
            if record.get("ownership") == "api"
            else False
        )
        confirmed = True
        if action in {"Delete", "Release override"}:
            st.warning(
                "Delete hides this record from active reads."
                if action == "Delete"
                else "Release allows a later API refresh to replace local corrections. It does not fetch data now."
            )
            confirmed = st.checkbox(
                "I confirm this action on the selected record", key=prefix + "confirm"
            )
        submit = st.form_submit_button("Apply " + action.lower())
    if submit:
        try:
            if not confirmed:
                raise ValueError("Confirm the action before applying it.")
            service = (
                PlayerService(database)
                if entity == "Players"
                else MatchStatsService(database)
            )
            if action == "Create":
                clean = _clean(entity, fields)
                if entity == "Players":
                    service.create(clean)
                else:
                    service.create(
                        entity,
                        relationship["innings_id"],
                        relationship["player_id"],
                        relationship["match_id"],
                        relationship["team_id"],
                        clean,
                    )
            else:
                args = (
                    [record["player_id"], record["version"]]
                    if entity == "Players"
                    else [
                        entity,
                        record["innings_id"],
                        record["player_id"],
                        record["version"],
                    ]
                )
                if action == "Edit":
                    service.update(*args, _clean(entity, fields), override=override)
                elif action == "Release override":
                    service.release_override(*args)
                else:
                    getattr(service, action.lower())(*args, override=override)
            st.session_state.pop("crud_token", None)
            st.session_state["crud_generation"] = (
                st.session_state.get("crud_generation", 0) + 1
            )
            st.session_state["crud_notice"] = (
                "Change committed. Saved records have been reloaded."
            )
            st.rerun()
        except StaleRecordError:
            log_event("crud_write", "stale_record", "CRUD")
            st.warning(
                "This record changed after you loaded it. Reload the selected record and review your edit before trying again."
            )
        except ValueError as error:
            st.warning(str(error))
        except (DatabaseError, SQLAlchemyError):
            log_event("crud_write", "database", "CRUD")
            st.warning(
                "The change could not be committed. Check access and database availability, then reload before retrying."
            )


def render_crud():
    """Render validated administrative forms for the selected dataset and access mode."""
    st.caption("CRICBUZZ LIVESTATS / RECORD MANAGEMENT")
    st.title("CRUD")
    st.write("Create, inspect and correct players and innings statistics.")
    if notice := st.session_state.pop("crud_notice", None):
        st.success(notice)
    try:
        settings = apply_preferences(load_settings())
        choice = st.selectbox(
            "Dataset",
            ["Configured dataset", "Saved sample", "Saved provider"],
            key="crud_dataset",
        )
        if choice != "Configured dataset":
            mode = "sample" if choice == "Saved sample" else "live"
            settings = replace(
                settings,
                data_mode=mode,
                database_url=None,
                read_database_url=None,
                database_path=PROJECT_ROOT / "data/runtime" / f"{mode}.db",
            )
        database = Database(settings)
        try:
            _page(database)
        finally:
            database.close()
    except ConfigurationError:
        st.error("Data settings need attention. Review the setup guide on Home.")
    except (DatabaseError, SQLAlchemyError, OSError):
        st.warning(
            "The selected database is unavailable. No automatic setup or repair is attempted."
        )
