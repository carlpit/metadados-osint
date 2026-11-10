"""Small helpers for normalizing metadata values."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def as_str(value: Any) -> str:
    """Convert EXIF/PDF/Office values into a readable string."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").rstrip("\x00").strip()
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denom = getattr(value, "denominator", 1) or 1
        number = float(value.numerator) / float(denom)
        return _format_number(number)
    return str(value).strip()


def decode_xp(value: Any) -> str:
    """Decode Windows XP* EXIF tags, which are stored as UTF-16LE."""

    if isinstance(value, bytes):
        return value.decode("utf-16-le", errors="replace").rstrip("\x00").strip()
    if isinstance(value, (tuple, list)) and value and isinstance(value[0], int):
        try:
            return bytes(value).decode("utf-16-le", errors="replace").rstrip("\x00").strip()
        except ValueError:
            return as_str(value)
    return as_str(value)


def to_float(value: Any) -> float:
    """Best-effort conversion of rationals, tuples and numbers to float."""

    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denom = getattr(value, "denominator", 1) or 1
        return float(value.numerator) / float(denom)
    if isinstance(value, tuple) and len(value) == 2 and not isinstance(value[0], tuple):
        denom = float(value[1] or 1)
        return float(value[0]) / denom
    return float(value)


def _format_number(number: float) -> str:
    if number.is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


def dms_to_decimal(dms: Any, ref: str) -> float:
    """Convert an EXIF GPS DMS triple into a signed decimal degree."""

    parts = list(dms)
    degrees = to_float(parts[0]) if parts else 0.0
    minutes = to_float(parts[1]) if len(parts) > 1 else 0.0
    seconds = to_float(parts[2]) if len(parts) > 2 else 0.0
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if str(ref).strip().upper() in {"S", "W"}:
        decimal = -decimal
    return decimal
