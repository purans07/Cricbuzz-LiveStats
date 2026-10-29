"""Isolated database fixtures; no test changes the working sample database."""

import shutil
from dataclasses import replace

import pytest

from config import load_settings
from database.initialize import initialize_database
from utils.db_connection import Database


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory):
    """Create one committed template, then copy it for each independent test."""
    path = tmp_path_factory.mktemp("template") / "sample.db"
    settings = replace(load_settings(environ={}), database_path=path)
    initialize_database(settings, seed_sample=True)
    return path


@pytest.fixture
def settings(tmp_path, seeded_template):
    """Return settings for a private per-test copy."""
    path = tmp_path / "sample.db"
    shutil.copy2(seeded_template, path)
    return replace(load_settings(environ={}), database_path=path)


@pytest.fixture
def database(settings):
    """Close engine resources after each test."""
    db = Database(settings)
    yield db
    db.close()


@pytest.fixture(autouse=True)
def block_real_requests(monkeypatch):
    """Tests must inject transport; never spend quota through real requests.send."""

    def blocked(*args, **kwargs):
        raise AssertionError(
            "Real HTTP is disabled in tests; inject a fixture transport."
        )

    monkeypatch.setattr("requests.sessions.Session.send", blocked)
