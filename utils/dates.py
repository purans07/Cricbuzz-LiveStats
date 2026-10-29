"""Strict dates and canonical UTC timestamps for persistence."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def normalize_timestamp(value: str) -> str:
    """Convert a timezone-aware ISO timestamp to second-precision UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise ValueError("Use a valid timezone-aware ISO timestamp.") from None
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone.")
    return parsed.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_date(value: str) -> str:
    """Require an actual date in YYYY-MM-DD form."""
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Date must use YYYY-MM-DD.")
    return value


def display_timestamp(value: str, timezone_name: str = "Asia/Kolkata") -> str:
    """Format a stored timestamp in the requested display timezone."""
    canonical = normalize_timestamp(value)
    return (
        datetime.fromisoformat(canonical.replace("Z", "+00:00"))
        .astimezone(ZoneInfo(timezone_name))
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )
