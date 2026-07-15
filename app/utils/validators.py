"""Reusable input validation helpers shared across routes and forms."""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLL_NUMBER_RE = re.compile(r"^[A-Za-z0-9]{4,50}$")


def is_valid_email(value: str) -> bool:
    return bool(value) and bool(EMAIL_RE.match(value.strip()))


def is_valid_roll_number(value: str) -> bool:
    return bool(value) and bool(ROLL_NUMBER_RE.match(value.strip()))


def is_valid_latitude(value) -> bool:
    try:
        return -90.0 <= float(value) <= 90.0
    except (TypeError, ValueError):
        return False


def is_valid_longitude(value) -> bool:
    try:
        return -180.0 <= float(value) <= 180.0
    except (TypeError, ValueError):
        return False


def is_valid_radius(value) -> bool:
    try:
        return 0 < float(value) <= 5000
    except (TypeError, ValueError):
        return False


def sanitize_text(value: str, max_length: int = 255) -> str:
    """Strip whitespace and enforce a max length on free-text inputs."""
    if value is None:
        return ""
    return value.strip()[:max_length]
