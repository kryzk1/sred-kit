"""Completeness of sred.toml and roster.csv against what each phase needs."""
from __future__ import annotations

import calendar
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import config
from .roster import load_roster

YN = {"Y", "N"}
ELIGIBILITY_KEYS = ["government_assistance", "client_contract_work", "funded_by_others", "work_outside_canada"]
CREDENTIAL_ENVS = {"gitlab": [("token_env", "GITLAB_TOKEN")], "linear": [("token_env", "LINEAR_API_KEY")],
                   "jira": [("email_env", "JIRA_EMAIL"), ("token_env", "JIRA_TOKEN")]}


@dataclass(frozen=True)
class Missing:
    phase: int
    where: str
    what: str

    def __str__(self) -> str:
        return f"MISSING [phase {self.phase}] {self.where}: {self.what}"


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def filing_deadline(fy_end: date) -> date:
    return add_months(fy_end, 18)


def current_phase(claim_dir: Path) -> int:
    state = Path(claim_dir) / "STATE.md"
    if state.exists():
        m = re.search(r"(?m)^phase:\s*(\d+)", state.read_text(encoding="utf-8"))
        if m:
            return int(m.group(1))
    return 2


def _get(cfg: dict, dotted: str):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _blank(v) -> bool:
    if v is None or isinstance(v, bool):
        return v is None
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (list, dict)):
        return not v
    if isinstance(v, (int, float)):
        return v == 0
    return False


def _num(v: str) -> bool:
    text = (v or "").replace(",", "").replace("$", "").strip()
    try:
        float(text)
    except ValueError:
        return False
    return True


def _check_sources(cfg: dict, missing: list[Missing], captured: set[str]) -> None:
    T = "sred.toml"
    srcs = config.sources(cfg)
    if not any(s.get("kind") == "code" for s in srcs):
        missing.append(Missing(2, T, 'sources: at least one source with kind = "code" (code history drives the time basis)'))
    for s in srcs:
        where = f"{T} [[sources]] {s.get('name') or '<unnamed>'}"
        method = s.get("method")
        for k in ("name", "kind", "tool", "method"):
            if _blank(s.get(k)) and not (k == "tool" and method == "git-log"):
                missing.append(Missing(2, where, k))
        if s.get("kind") and s["kind"] not in config.VALID_KINDS:
            missing.append(Missing(2, where, f"kind must be one of {sorted(config.VALID_KINDS)}"))
        if method and method not in config.VALID_METHODS:
            missing.append(Missing(2, where, f"method must be one of {sorted(config.VALID_METHODS)}"))
        if method == "api":
            tool = s.get("tool")
            if tool not in config.API_TOOLS:
                missing.append(Missing(2, where, f"no API adapter for tool {tool!r}; use export or connector"))
            for key, default in CREDENTIAL_ENVS.get(tool, []):
                env = s.get(key, default)
                if s.get("name") not in captured and not os.environ.get(env):  # once captured, access may lapse
                    missing.append(Missing(2, where, f"environment variable {env} is not set"))
            if tool == "github" and _blank(s.get("org")) and _blank(s.get("repos")):
                missing.append(Missing(2, where, "org or repos"))
            if tool == "gitlab" and _blank(s.get("projects")):
                missing.append(Missing(2, where, "projects"))
            if tool == "jira" and _blank(s.get("base_url")):
                missing.append(Missing(2, where, "base_url"))
        if method == "export":
            if _blank(s.get("mapping")):
                missing.append(Missing(2, where, "mapping (preset name or path)"))
            p = s.get("export_path")
            if _blank(p) or not config.resolve_path(cfg, p).exists():
                missing.append(Missing(2, where, f"export_path file not found: {p!r}"))
        if method == "git-log" and _blank(s.get("paths")):
            missing.append(Missing(2, where, "paths (local clones)"))


def _check_roster(claim_dir: Path, missing: list[Missing]) -> None:
    path = claim_dir / "roster.csv"
    if not path.exists():
        missing.append(Missing(2, "roster.csv", "file not found (copy templates/roster.csv)"))
        return
    roster = load_roster(path)
    if not roster:
        missing.append(Missing(2, "roster.csv", "no people listed"))
    for r in roster:
        who = f"roster.csv {r['id'] or r['name'] or '<row>'}"
        for k in ("id", "name"):
            if not r[k]:
                missing.append(Missing(2, who, k))
        if r["classification"] not in ("employee", "contractor"):
            missing.append(Missing(2, who, "classification must be employee or contractor"))
        if not r["aliases"]:
            missing.append(Missing(2, who, "aliases (tool handles or email) for identity matching"))
        for k in ("in_canada", "specified_employee"):
            if r[k] not in YN:
                missing.append(Missing(6, who, f"{k} (Y or N)"))
        if not _num(r["wages_earned"]):
            missing.append(Missing(6, who, "wages_earned"))
        if r["classification"] == "employee" and not _num(r["paid_hours"]):
            missing.append(Missing(6, who, "paid_hours"))
        if r["classification"] == "contractor":
            for k in ("arms_length", "contract_provided", "sred_in_contract"):
                if r[k] not in YN:
                    missing.append(Missing(6, who, f"{k} (Y or N)"))


def check_setup(claim_dir: Path) -> tuple[list[Missing], list[str]]:
    claim_dir = Path(claim_dir)
    missing: list[Missing] = []
    info: list[str] = []
    cfg_path = claim_dir / "sred.toml"
    if not cfg_path.exists():
        return [Missing(1, "sred.toml", "file not found (copy templates/sred.toml)")], info
    cfg = config.load_config(cfg_path)
    T = "sred.toml"

    def need(phase: int, dotted: str, what: str) -> None:
        if _blank(_get(cfg, dotted)):
            missing.append(Missing(phase, T, f"{dotted}: {what}"))

    need(2, "company.name", "legal company name")
    try:
        _, end = config.fiscal_year(cfg)
        info.append(f"Filing deadline: {filing_deadline(end).isoformat()} (fiscal year end + 18 months)")
    except config.ConfigError as exc:
        missing.append(Missing(2, T, f"fiscal_year: {exc}"))
    manifest = claim_dir / "evidence" / "raw" / "MANIFEST.json"
    captured = set(json.loads(manifest.read_text(encoding="utf-8")).get("sources", {})) if manifest.exists() else set()
    _check_sources(cfg, missing, captured)
    _check_roster(claim_dir, missing)
    if not isinstance(_get(cfg, "claim.first_claim"), bool):
        missing.append(Missing(3, T, "claim.first_claim: true or false"))
    elif not cfg["claim"]["first_claim"]:
        need(3, "claim.prior_filings", "prior T661 Part 2 filings (PDF paths)")
        need(3, "claim.prior_titles", "project titles exactly as previously filed")
        for p in _get(cfg, "claim.prior_filings") or []:
            if not config.resolve_path(cfg, p).exists():
                missing.append(Missing(3, T, f"claim.prior_filings: file not found {p!r}"))
    for k in ELIGIBILITY_KEYS:
        need(3, f"eligibility.{k}", 'answer, or "none"')
    need(3, "preparer.ratifier", "who approves locked decisions")
    need(6, "payroll.total_wages_earned", "employees' earned wages for the fiscal year from payroll (contractors excluded), to reconcile the roster")
    need(7, "preparer.accountant", "accountant or preparer name")
    need(7, "limits.mode", "ask the preparer whether their filing software enforces words or lines")
    return sorted(missing, key=lambda m: (m.phase, m.where, m.what)), info
