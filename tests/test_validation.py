"""Boundary tests for configuration, primitive records and cricket units."""

import pytest

from config import PROJECT_ROOT, ConfigurationError, load_settings
from models.records import validate_record
from utils.cricket import balls_to_overs, overs_to_balls
from utils.dates import display_timestamp, normalize_timestamp, validate_date


@pytest.mark.parametrize("overs,balls", [("4.2", 26), (0, 0), ("10", 60), ("0.5", 5)])
def test_overs_conversion(overs, balls):
    assert overs_to_balls(overs) == balls
    assert overs_to_balls(balls_to_overs(balls)) == balls


@pytest.mark.parametrize("value", [4.2, True, "4.6", "-1", "4.12", "nan", " 4.2"])
def test_invalid_overs(value):
    with pytest.raises(ValueError):
        overs_to_balls(value)


@pytest.mark.parametrize("value", [-1, 1.5, True])
def test_invalid_legal_balls(value):
    with pytest.raises(ValueError):
        balls_to_overs(value)


def test_utc_and_local_display():
    assert normalize_timestamp("2026-10-21T12:30:00+05:30") == "2026-10-21T07:00:00Z"
    assert display_timestamp("2026-10-21T07:00:00Z").endswith("12:30:00 IST")


@pytest.mark.parametrize("value", ["2026-10-21", "2026-02-30T00:00:00Z", "garbage"])
def test_invalid_timestamp(value):
    with pytest.raises(ValueError):
        normalize_timestamp(value)


def test_date_validation():
    assert validate_date("2024-02-29") == "2024-02-29"
    with pytest.raises(ValueError):
        validate_date("2026-02-29")


def test_record_retains_unknown_and_known_zero():
    assert validate_record(
        {"runs": None, "balls_faced": 0}, {"runs": "INTEGER", "balls_faced": "INTEGER"}
    ) == {
        "runs": None,
        "balls_faced": 0,
    }


@pytest.mark.parametrize("value", [-1, 1.5, True, "12"])
def test_record_integer_validation(value):
    with pytest.raises(ValueError):
        validate_record({"runs": value}, {"runs": "INTEGER"})


def test_unknown_column_rejected():
    with pytest.raises(ValueError):
        validate_record({'runs"; DROP TABLE players; --': 1}, {"runs": "INTEGER"})


def test_blank_name_and_nonfinite_ratio_rejected():
    with pytest.raises(ValueError):
        validate_record({"full_name": " "}, {"full_name": "TEXT"})
    with pytest.raises(ValueError):
        validate_record({"ratio": float("nan")}, {"ratio": "REAL"})


def test_defaults_are_project_relative_and_need_no_api_key():
    settings = load_settings(environ={})
    assert settings.data_mode == "sample"
    assert settings.database_path == PROJECT_ROOT / "data/runtime/sample.db"


@pytest.mark.parametrize(
    "environment",
    [
        {"DATA_MODE": "production"},
        {"DATABASE_URL": "postgresql://user:secret@host/db"},
        {"DATABASE_URL": "sqlite:///:memory:"},
        {"DATABASE_URL": "sqlite:///db?mode=ro"},
        {"DISPLAY_TIMEZONE": "Not/AZone"},
        {"APP_ACCESS_MODE": "admin"},
    ],
)
def test_invalid_config_is_safe(environment):
    with pytest.raises(ConfigurationError) as caught:
        load_settings(environ=environment)
    assert "secret" not in str(caught.value)


def test_live_mode_has_different_default_target():
    assert load_settings(environ={"DATA_MODE": "live"}).database_path.name == "live.db"


def test_environment_overrides_dotenv(tmp_path, monkeypatch):
    file = tmp_path / "private.env"
    file.write_text("DATA_MODE=live\nDISPLAY_TIMEZONE=UTC\n")
    monkeypatch.setenv("DATA_MODE", "sample")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DISPLAY_TIMEZONE", raising=False)
    monkeypatch.delenv("APP_ACCESS_MODE", raising=False)
    assert load_settings(env_file=file).data_mode == "sample"
    assert load_settings(env_file=file).display_timezone == "UTC"
