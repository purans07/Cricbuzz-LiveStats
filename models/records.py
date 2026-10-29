"""Validation shared by seed loading and later service/repository operations."""

import math

from utils.dates import normalize_timestamp, validate_date

FLAGS = {"is_international", "is_deleted", "is_dismissed", "is_super_over"}
DATES = {"valid_from", "valid_to", "start_date", "end_date"}
TIMESTAMPS = {
    "updated_at",
    "starts_at",
    "completed_at",
    "fetched_at",
    "upstream_updated_at",
}


def validate_record(record: dict, column_types: dict[str, str]) -> dict:
    """Reject unknown columns and invalid primitive values; retain unknowns."""
    unknown = set(record) - set(column_types)
    if unknown:
        raise ValueError(f"Unknown record columns: {', '.join(sorted(unknown))}")
    result = dict(record)
    for key, value in record.items():
        if value is None:
            continue
        kind = column_types[key].upper()
        if kind.startswith(("VARCHAR", "CHAR")):
            kind = "TEXT"
        elif kind in {"FLOAT", "DOUBLE PRECISION", "DOUBLE"}:
            kind = "REAL"
        if kind == "INTEGER" and type(value) is not int:
            raise ValueError(f"{key} must be an integer or unknown.")
        if kind == "REAL" and (
            type(value) not in {int, float} or not math.isfinite(value)
        ):
            raise ValueError(f"{key} must be a finite number or unknown.")
        if kind == "TEXT" and not isinstance(value, str):
            raise ValueError(f"{key} must be text or unknown.")
        if kind == "INTEGER" and value < 0:
            raise ValueError(f"{key} must not be negative.")
        if key in FLAGS and value not in {0, 1}:
            raise ValueError(f"{key} must be zero or one.")
        if key in DATES:
            result[key] = validate_date(value)
        if key in TIMESTAMPS:
            result[key] = normalize_timestamp(value)
        if key == "full_name" and not value.strip():
            raise ValueError("Player full name is required.")
    return result
