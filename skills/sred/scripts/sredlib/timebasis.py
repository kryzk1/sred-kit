"""Evidence-day time basis: ledger, monthly shares, gap months, person summary, labour summary."""
from __future__ import annotations

import csv
import fnmatch
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from . import activity

SCENARIOS = {"conservative": {"direct"}, "balanced": {"direct", "support"}, "maximum": {"direct", "support", "borderline"}}
LEVELS = {"direct", "support", "borderline", "none"}
LEDGER_COLUMNS = ["source", "key", "kind", "person", "date", "weight", "container", "title", "project", "level",
                  "category", "classified_by", "confidence", "reason", "needs_review"]
OVERRIDE_COLUMNS = ["source", "key", "project", "level", "category", "classified_by", "confidence", "reason"]
TIME_BASIS_COLUMNS = ["person", "month", "evidence_days", "sred_days", "share", "by_project", "gap"]
GAP_COLUMNS = ["person", "month", "basis", "basis_source", "corroborated", "basis_share"]
SUMMARY_COLUMNS = ["person", "name", "classification", "months_employed", "months_with_evidence", "gap_months",
                   "evidence_share", "proposed_pct", "confirmed_pct", "basis", "override_reason", "flags"]


class TimeBasisError(ValueError):
    pass


def _read_csv(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})


def match_rule(rule: dict, row: dict) -> bool:
    """Every condition the rule sets must hold. Globs use fnmatch (`*` also matches `/`)."""
    for f in ("source", "container"):
        if rule.get(f) and not fnmatch.fnmatchcase(row.get(f, ""), rule[f]):
            return False
    if rule.get("kind") and row.get("kind") != rule["kind"]:
        return False
    if rule.get("tags") and not any(fnmatch.fnmatchcase(t, rule["tags"]) for t in activity.split(row.get("tags", ""))):
        return False
    if rule.get("paths") and not any(fnmatch.fnmatchcase(p, rule["paths"]) for p in activity.split(row.get("paths", ""))):
        return False
    if rule.get("title") and not re.search(rule["title"], row.get("title", "")):
        return False
    return True


def classify(rows: list[dict], rules: list[dict], overrides: list[dict], threshold: float) -> list[dict]:
    by_key = {(o["source"], o["key"]): o for o in overrides}
    ledger = []
    for r in rows:
        if r["person"] == "bot" or r["person"].startswith("unmatched:"):
            continue
        where = f"{r['source']}:{r['key']}"
        o = by_key.get((r["source"], r["key"]))
        rule = next((ru for ru in rules if match_rule(ru, r)), None)
        if o and o.get("classified_by") == "claimant":
            src, by, conf = o, "claimant", 1.0
        elif rule:
            src, by, conf = rule, f"rule:{rule.get('id', '?')}", 1.0
        elif o:
            src, by, conf = o, o.get("classified_by") or "claude", float(o.get("confidence") or 0)
        else:
            src, by, conf = {"level": "none", "category": "unclassified"}, "", 0.0
        level = src.get("level") or "none"
        if level not in LEVELS:
            raise TimeBasisError(f"{where}: level must be one of {sorted(LEVELS)}, got {level!r}")
        project = "" if level == "none" else (src.get("project") or "")
        if level != "none" and project in ("", "none"):
            raise TimeBasisError(f"{where}: level {level!r} needs a project")
        needs = by == "" or (by == "claude" and conf < threshold)
        entry = {k: r.get(k, "") for k in ("source", "key", "kind", "person", "date", "weight", "container", "title")}
        entry.update(project=project, level=level, category=src.get("category", "") if level == "none" else "",
                     classified_by=by, confidence=f"{conf:.2f}", reason=src.get("reason", ""), needs_review="Y" if needs else "N")
        ledger.append(entry)
    return ledger


def _counts_as_evidence(e: dict, scenario: str) -> bool:
    return scenario != "conservative" or e["weight"] == "verbatim"


def _counts_as_sred(e: dict, scenario: str) -> bool:
    return e["level"] in SCENARIOS[scenario] and bool(e["project"])


def monthly(ledger: list[dict], scenario: str, kind_weights: dict[str, float]) -> dict:
    days = defaultdict(lambda: {"total": 0.0, "sred": 0.0, "proj": defaultdict(float)})
    for e in ledger:
        if not _counts_as_evidence(e, scenario):
            continue
        w = kind_weights.get(e["kind"], 1.0)
        d = days[(e["person"], e["date"])]
        d["total"] += w
        if _counts_as_sred(e, scenario):
            d["sred"] += w
            d["proj"][e["project"]] += w
    months = defaultdict(lambda: {"evidence_days": 0, "sred_days": 0.0, "by_project": defaultdict(float)})
    for (person, day), d in sorted(days.items()):
        if d["total"] <= 0:
            continue
        m = months[(person, day[:7])]
        m["evidence_days"] += 1
        m["sred_days"] += d["sred"] / d["total"]
        for p, w in d["proj"].items():
            m["by_project"][p] += w / d["total"]
    return dict(months)


def month_range(start: date, end: date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def employed_months(person: dict, fy: tuple[date, date]) -> list[str]:
    start, end = fy
    s = max(date.fromisoformat(person["start"]) if person.get("start") else start, start)
    e = min(date.fromisoformat(person["end"]) if person.get("end") else end, end)
    return month_range(s, e) if s <= e else []


def merge_gaps(existing: list[dict], gaps: list[tuple[str, str]]) -> list[dict]:
    keep = {(g["person"], g["month"]): g for g in existing}
    blank = {"basis": "", "basis_source": "", "corroborated": "", "basis_share": ""}
    return [keep.get((person, month)) or {"person": person, "month": month, **blank} for person, month in gaps]


def gap_share(g: dict, scenario: str) -> float:
    if scenario == "conservative" or not (g.get("basis") or "").strip():
        return 0.0
    if scenario == "balanced" and (g.get("corroborated") or "").strip().upper() != "Y":
        return 0.0
    try:
        return max(0.0, min(100.0, float(g.get("basis_share") or 0))) / 100
    except ValueError as exc:
        raise TimeBasisError(f"gap_months.csv {g['person']} {g['month']}: basis_share must be a number 0-100") from exc
