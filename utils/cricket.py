"""Cricket unit conversion; overs notation is not a decimal fraction."""

import re


def overs_to_balls(value: str | int) -> int:
    """Convert e.g. '4.2' to 26; reject floats and ball suffixes above five."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Supply overs as text or a whole number, never a float.")
    match = re.fullmatch(r"(0|[1-9][0-9]*)(?:\.([0-5]))?", str(value))
    if not match:
        raise ValueError("Overs must contain whole overs and zero to five balls.")
    return int(match[1]) * 6 + int(match[2] or 0)


def balls_to_overs(value: int) -> str:
    """Format a known non-negative legal-ball count as cricket overs."""
    if type(value) is not int or value < 0:
        raise ValueError("Legal balls must be a non-negative integer.")
    return f"{value // 6}.{value % 6}"
