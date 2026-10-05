"""Load and query sred.toml."""
from __future__ import annotations

import tomllib
from datetime import date, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VALID_KINDS = {"code", "tracker", "chat", "meetings", "docs"}
VALID_METHODS = {"api", "export", "connector", "git-log"}
API_TOOLS = {"github", "gitlab", "linear", "jira"}
DEFAULT_LIMITS = {
    "mode": "words",
    "words": {"242": 350, "244": 700, "246": 350},
    "lines": {"242": 50, "244": 100, "246": 50},
    "line_width": 78,
}


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> dict:
    path = Path(path)
    with path.open("rb") as fh:
        cfg = tomllib.load(fh)
    cfg["_path"] = path
    cfg["_dir"] = path.parent
    return cfg


def fiscal_year(cfg: dict) -> tuple[date, date]:
    fy = cfg.get("fiscal_year") or {}
    start, end = fy.get("start"), fy.get("end")
    if not isinstance(start, date) or not isinstance(end, date):
        raise ConfigError("fiscal_year.start and fiscal_year.end must be TOML dates (YYYY-MM-DD, unquoted)")
    if end <= start:
        raise ConfigError("fiscal_year.end must be after fiscal_year.start")
    return start, end


def sources(cfg: dict) -> list[dict]:
    return list(cfg.get("sources") or [])


def source(cfg: dict, name: str) -> dict:
    for s in sources(cfg):
        if s.get("name") == name:
            return s
    raise ConfigError(f"no source named {name!r} in sred.toml")


def limits(cfg: dict) -> dict:
    user = cfg.get("limits") or {}
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_LIMITS.items()}
    for key in ("words", "lines"):
        for line, val in (user.get(key) or {}).items():
            out[key][str(line)] = int(val)
    if user.get("mode"):  # blank until onboarding asks the preparer; the form's word limits apply meanwhile
        out["mode"] = user["mode"]
    if "line_width" in user:
        out["line_width"] = int(user["line_width"])
    if out["mode"] not in ("words", "lines"):
        raise ConfigError("limits.mode must be 'words' or 'lines'")
    return out


def issue_key_regexes(cfg: dict) -> list[str]:
    return [s["issue_key_regex"] for s in sources(cfg) if s.get("issue_key_regex")]


def classification(cfg: dict) -> dict:
    c = cfg.get("classification") or {}
    return {"review_threshold": float(c.get("review_threshold", 0.7)), "rules": list(c.get("rules") or [])}


def rates(cfg: dict) -> dict | None:
    r = cfg.get("rates") or {}
    out = {k: float(r[k]) for k in ("itc_rate", "proxy_rate", "contract_rate") if k in r}
    return out or None


def kind_weights(cfg: dict) -> dict[str, float]:
    weights = (cfg.get("time_basis") or {}).get("kind_weights") or {}
    return {k: float(v) for k, v in weights.items()}


def timezone_of(cfg: dict) -> tzinfo:
    name = (cfg.get("company") or {}).get("timezone")
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ConfigError(f"company.timezone {name!r} is not a known time zone (e.g. America/Toronto)") from exc


def resolve_path(cfg: dict, p: str) -> Path:
    path = Path(p)
    return path if path.is_absolute() else Path(cfg["_dir"]) / path
