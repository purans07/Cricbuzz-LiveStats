"""Real form events on temporary datasets; no working-data mutations."""

from dataclasses import replace

import pytest
from streamlit.testing.v1 import AppTest

from config import PROJECT_ROOT
from services.crud_catalog import CrudCatalog
from services.players import PlayerService
from ui.crud import optional_integer


def page(settings, monkeypatch):
    monkeypatch.setattr("ui.crud.load_settings", lambda: settings)
    return AppTest.from_file(
        str(PROJECT_ROOT / "pages/05_CRUD.py"), default_timeout=15
    ).run()


def field(at, label):
    return next(x for x in at.text_input if x.label == label)


def apply(at, action):
    return at.button(key="FormSubmitter:crud_form-Apply " + action).click().run()


def test_create_profile_and_reset_form(settings, database, monkeypatch):
    at = page(settings, monkeypatch)
    field(at, "Player name").set_value("New Learner")
    apply(at, "create")
    assert not at.exception and at.success
    assert len(PlayerService(database).list()) == 13
    assert field(at, "Player name").value == ""


def test_edit_delete_confirmation_and_restore(settings, database, monkeypatch):
    at = page(settings, monkeypatch)
    at.selectbox(key="crud_action").select("Edit").run()
    field(at, "Player name").set_value("Edited name")
    apply(at, "edit")
    assert PlayerService(database).get(1)["full_name"] == "Edited name"
    at.selectbox(key="crud_action").select("Delete").run()
    apply(at, "delete")
    assert at.warning and PlayerService(database).get(1)
    at.checkbox[0].check()
    apply(at, "delete")
    assert PlayerService(database).get(1) is None
    at.selectbox(key="crud_action").select("Restore").run()
    apply(at, "restore")
    assert not at.exception and PlayerService(database).get(1)


def test_stale_form_does_not_overwrite_newer_version(settings, database, monkeypatch):
    at = page(settings, monkeypatch)
    at.selectbox(key="crud_action").select("Edit").run()
    field(at, "Player name").set_value("Stale edit")
    PlayerService(database).update(1, 1, {"full_name": "Concurrent edit"})
    apply(at, "edit")
    assert not at.exception and any("changed after" in x.value for x in at.warning)
    assert PlayerService(database).get(1)["full_name"] == "Concurrent edit"
    at.button(key="crud_reload").click().run()
    assert field(at, "Player name").value == "Concurrent edit"


def test_api_ownership_requires_checkbox_then_protects_override(
    settings, database, monkeypatch
):
    with database.transaction(write=True) as c:
        c.exec_driver_sql("UPDATE players SET ownership='api' WHERE player_id=1")
    at = page(settings, monkeypatch)
    at.selectbox(key="crud_action").select("Edit").run()
    field(at, "Player name").set_value("Local correction")
    apply(at, "edit")
    assert at.warning and PlayerService(database).get(1)["ownership"] == "api"
    at.checkbox[0].check()
    apply(at, "edit")
    assert PlayerService(database).get(1)["ownership"] == "override"
    at.selectbox(key="crud_action").select("Release override").run()
    at.checkbox[0].check()
    apply(at, "release override")
    assert PlayerService(database).get(1)["ownership"] == "api"


@pytest.mark.parametrize("kind", ["batting", "bowling", "fielding"])
def test_stat_form_edits_existing_record(settings, database, monkeypatch, kind):
    at = page(settings, monkeypatch)
    at.selectbox(key="crud_entity").select(kind).run()
    at.selectbox(key="crud_action").select("Edit").run()
    label = (
        "Runs"
        if kind == "batting"
        else "Runs conceded"
        if kind == "bowling"
        else "Catches"
    )
    field(at, label).set_value("999" if kind == "batting" else "3")
    apply(at, "edit")
    assert not at.exception and at.success
    key = (
        "runs"
        if kind == "batting"
        else "runs_conceded"
        if kind == "bowling"
        else "catches"
    )
    assert CrudCatalog(database).records(kind)[0][key] == (
        999 if kind == "batting" else 3
    )


def test_readonly_forms_hidden_and_missing_target(settings, monkeypatch, tmp_path):
    at = page(replace(settings, access_mode="public_readonly"), monkeypatch)
    assert not at.exception and at.dataframe and not at.form
    target = tmp_path / "missing.db"
    at = page(replace(settings, database_path=target), monkeypatch)
    assert at.warning and not at.exception and not target.exists()


def test_blank_zero_and_invalid_integer():
    assert optional_integer("") is None
    assert optional_integer("0") == 0
    for value in ("-1", "4.2", "True"):
        with pytest.raises(ValueError):
            optional_integer(value)


def test_catalog_relationships_follow_service_team_rules(database):
    cat = CrudCatalog(database)
    with database.transaction() as c:
        for kind, side in [
            ("batting", "batting_team_id"),
            ("bowling", "bowling_team_id"),
            ("fielding", "bowling_team_id"),
        ]:
            for row in cat.eligible(kind)[:20]:
                assert (
                    row["team_id"]
                    == c.exec_driver_sql(
                        f"SELECT {side} FROM innings WHERE innings_id=?",
                        (row["innings_id"],),
                    ).scalar_one()
                )


@pytest.mark.parametrize("kind", ["batting", "bowling", "fielding"])
def test_create_stat_from_valid_participation(settings, database, monkeypatch, kind):
    target = CrudCatalog(database).eligible(kind)[0]
    table = kind + "_performances"
    with database.transaction(write=True) as c:
        c.exec_driver_sql(
            f"DELETE FROM {table} WHERE innings_id=? AND player_id=?",
            (target["innings_id"], target["player_id"]),
        )
    at = page(settings, monkeypatch)
    at.selectbox(key="crud_entity").select(kind).run()
    field(
        at,
        "Runs"
        if kind == "batting"
        else "Runs conceded"
        if kind == "bowling"
        else "Catches",
    ).set_value("0")
    apply(at, "create")
    assert not at.exception and at.success
    created = next(
        r
        for r in CrudCatalog(database).records(kind)
        if r["innings_id"] == target["innings_id"]
        and r["player_id"] == target["player_id"]
    )
    assert created["ownership"] == "manual"
