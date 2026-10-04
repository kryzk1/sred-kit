"""Timestamp parsing shared by every adapter and mapping."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_OFFSET_RE = re.compile(r"([+-]\d{2})(\d{2})$")


def parse_iso(value: str, default_tz=None) -> datetime:
    """Parse ISO 8601, accepting a trailing Z and +HHMM offsets. Naive values get default_tz (UTC if None)."""
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    v = _OFFSET_RE.sub(r"\1:\2", v)
    dt = datetime.fromisoformat(v)
    return dt if dt.tzinfo else dt.replace(tzinfo=default_tz or timezone.utc)


def iso(ts: datetime) -> str:
    """UTC ISO 8601 with a trailing Z."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str, formats: list[str], default_tz=None) -> datetime | None:
    """Try each format in order. Special formats: iso, epoch, epoch_ms, js (Linear CSV).

    Values without a time zone (including date-only values) are read in default_tz (UTC if None).
    Returns None for an empty value; raises ValueError naming the value if nothing parses.
    """
    v = (value or "").strip()
    if not v:
        return None
    for fmt in formats:
        try:
            if fmt == "iso":
                return parse_iso(v, default_tz)
            if fmt == "epoch":
                return datetime.fromtimestamp(float(v), tz=timezone.utc)
            if fmt == "epoch_ms":
                return datetime.fromtimestamp(float(v) / 1000, tz=timezone.utc)
            if fmt == "js":
                core = re.sub(r"\s*\(.*\)$", "", v)
                return datetime.strptime(core, "%a %b %d %Y %H:%M:%S GMT%z")
            dt = datetime.strptime(v, fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=default_tz or timezone.utc)
        except (ValueError, OverflowError, OSError):
            continue
    raise ValueError(f"could not parse date {value!r} with formats {formats}")
