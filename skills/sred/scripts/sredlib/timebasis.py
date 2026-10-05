"""Evidence-day time basis: ledger, monthly shares, gap months, person summary, labour summary."""
from __future__ import annotations

import csv
import fnmatch
import json
import re
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from . import activity, config
from .roster import load_roster

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


MONTH_NAMES = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def normalize_month(value: str) -> str:
    """'2026-10', '2026-10-01', '10/2026', 'Oct-26', 'Oct 2026', 'October 2026' -> '2026-10'.

    Spreadsheet programs rewrite month keys when a claimant edits the CSV; unrecognized values pass through.
    """
    v = (value or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?", v)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"(\d{1,2})/(\d{4})", v)
    if m:
        return f"{int(m.group(2)):04d}-{int(m.group(1)):02d}"
    m = re.fullmatch(r"([A-Za-z]{3})[A-Za-z]*[-\s']+(\d{2}|\d{4})", v)
    if m and m.group(1).lower() in MONTH_NAMES:
        year = int(m.group(2)) + (2000 if len(m.group(2)) == 2 else 0)
        return f"{year:04d}-{MONTH_NAMES[m.group(1).lower()]:02d}"
    return v


def merge_gaps(existing: list[dict], gaps: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Gap rows for this run, plus claimant entries that no longer match a gap month (kept, never dropped)."""
    keep = {(g["person"], normalize_month(g["month"])): {**g, "month": normalize_month(g["month"])} for g in existing}
    blank = {"basis": "", "basis_source": "", "corroborated": "", "basis_share": ""}
    rows = [keep.pop((person, month), None) or {"person": person, "month": month, **blank} for person, month in gaps]
    leftovers = [g for g in keep.values() if (g.get("basis") or "").strip()]
    return rows, leftovers


def gap_share(g: dict, scenario: str) -> float:
    if scenario == "conservative" or not (g.get("basis") or "").strip():
        return 0.0
    if scenario == "balanced" and (g.get("corroborated") or "").strip().upper() != "Y":
        return 0.0
    try:
        return max(0.0, min(100.0, float(g.get("basis_share") or 0))) / 100
    except ValueError as exc:
        raise TimeBasisError(f"gap_months.csv {g['person']} {g['month']}: basis_share must be a number 0-100") from exc


DEFAULT_COLUMNS_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / "labour-summary-columns.csv"
MONEY_FIELDS = ("paid_hours", "wages_paid", "wages_earned", "bonus", "taxable_benefits", "pay_in_lieu")


def _pct(v, who: str = ""):
    """A percentage typed by the claimant: blank -> None; otherwise a number from 0 to 100."""
    text = (v or "").strip().rstrip("%").strip()
    if not text:
        return None
    try:
        pct = float(text)
    except ValueError:
        raise TimeBasisError(f"{who or 'person_summary.csv'}: confirmed_pct {v!r} is not a number (write e.g. 75 or 75%)") from None
    if not 0 <= pct <= 100:
        raise TimeBasisError(f"{who or 'person_summary.csv'}: confirmed_pct {v!r} must be between 0 and 100")
    return pct


def _effective(s: dict) -> float:
    c = _pct(s.get("confirmed_pct"))
    return c if c is not None else float(s.get("proposed_pct") or 0)


def summarize(roster, months, gap_rows, fy, scenario, previous, use_confirmed: bool = True) -> list[dict]:
    gap_by = {(g["person"], g["month"]): g for g in gap_rows}
    prev = {p["person"]: p for p in previous} if use_confirmed else {}
    for pid, p in prev.items():
        _pct(p.get("confirmed_pct"), pid)  # fail early, naming the person, before any number is written
    out = []
    for r in roster:
        pid = r["id"]
        emp = employed_months(r, fy)
        shares, ev_days, sred_days, with_ev, gap_n = [], 0, 0.0, 0, 0
        for month in emp:
            m = months.get((pid, month))
            if m and m["evidence_days"]:
                shares.append(m["sred_days"] / m["evidence_days"])
                with_ev += 1
                ev_days += m["evidence_days"]
                sred_days += m["sred_days"]
            else:
                gap_n += 1
                shares.append(gap_share(gap_by.get((pid, month), {}), scenario))
        proposed = round(100 * sum(shares) / len(shares), 2) if shares else 0.0
        p = prev.get(pid, {})
        out.append({
            "person": pid, "name": r["name"], "classification": r["classification"], "months_employed": len(emp),
            "months_with_evidence": with_ev, "gap_months": gap_n,
            "evidence_share": f"{(100 * sred_days / ev_days) if ev_days else 0:.2f}", "proposed_pct": f"{proposed:.2f}",
            "confirmed_pct": p.get("confirmed_pct", "") or "", "basis": p.get("basis", "") or "",
            "override_reason": p.get("override_reason", "") or "", "flags": "",
        })
    _flag(out, roster)
    return out


def _flag(summary: list[dict], roster: list[dict]) -> None:
    by_id = {r["id"]: r for r in roster}
    classes = defaultdict(set)
    for r in roster:
        classes[r["name"].strip().lower()].add(r["classification"])
    claimed = [_effective(s) for s in summary if _effective(s) > 0]
    identical = len(claimed) >= 2 and len(set(claimed)) == 1
    for s in summary:
        r, pct, flags = by_id[s["person"]], _effective(s), []
        conf = _pct(s["confirmed_pct"])
        if conf is None:
            flags.append("UNCONFIRMED")
        if identical and pct > 0:
            flags.append("IDENTICAL_PCT")
        if pct > 90 and not s["basis"].strip():
            flags.append("OVER_90_NO_BASIS")
        if r.get("in_canada") == "N" and pct > 0:
            flags.append("OUTSIDE_CANADA")
        if len(classes[r["name"].strip().lower()]) > 1:
            flags.append("DUAL_ROLE")
        if conf is not None and abs(conf - float(s["proposed_pct"])) > 15 and not s["override_reason"].strip():
            flags.append("OVERRIDE_NO_REASON")
        if pct > 0 and s["months_with_evidence"] < 3:
            flags.append("THIN_EVIDENCE")
        s["flags"] = ";".join(flags)


def money(v) -> Decimal:
    text = str(v or "").replace(",", "").replace("$", "").strip()
    return Decimal(text) if text else Decimal("0")


def q2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def load_columns(cfg: dict) -> list[tuple[str, str]]:
    custom = (cfg.get("preparer") or {}).get("labour_template")
    path = config.resolve_path(cfg, custom) if custom else DEFAULT_COLUMNS_PATH
    return [(r["column"], r["field"]) for r in _read_csv(path)]


def labour_summary(roster, summary, columns) -> list[list[str]]:
    by_id = {s["person"]: s for s in summary}
    rows = [[c for c, _ in columns]]
    totals = defaultdict(lambda: Decimal("0"))
    for r in roster:
        s = by_id[r["id"]]
        conf = _pct(s.get("confirmed_pct"))
        pct = Decimal(str(_effective(s)))
        frac = pct / 100
        employee = r["classification"] == "employee"
        earned = money(r["wages_earned"])
        sred_hours = q2(money(r["paid_hours"]) * frac) if employee else None
        sred_wages = q2(earned * frac)
        basis = (s.get("basis") or "").strip() or ("" if conf is not None else "PROPOSED - not confirmed")
        fields = {**r, "classification_label": "Employee" if employee else "Subcontractor", "sred_pct": f"{q2(pct)}%",
                  "sred_eligible": "TRUE" if pct > 0 else "FALSE", "sred_hours": "" if sred_hours is None else str(sred_hours),
                  "sred_wages": str(sred_wages), "basis": basis}
        rows.append([str(fields.get(f, "")) for _, f in columns])
        for f in MONEY_FIELDS:
            totals[f] += money(r.get(f, ""))
        totals["sred_hours"] += sred_hours or Decimal("0")
        totals["sred_wages"] += sred_wages
        if pct > 0:
            totals["eligible_earned"] += earned
    weighted = q2(100 * totals["sred_wages"] / totals["eligible_earned"]) if totals["eligible_earned"] else Decimal("0.00")
    total = {"name": "TOTAL", "sred_pct": f"{weighted}%", "basis": "SRED % weighted by earned wages of people claimed",
             **{f: str(q2(totals[f])) for f in MONEY_FIELDS + ("sred_hours", "sred_wages")}}
    rows.append([total.get(f, "") for _, f in columns])
    return rows


def scenario_totals(roster, summary, cfg) -> dict:
    by_id = {s["person"]: s for s in summary}
    emp, con = Decimal("0"), Decimal("0")
    for r in roster:
        amount = q2(money(r["wages_earned"]) * Decimal(str(_effective(by_id[r["id"]]))) / 100)
        if r["classification"] == "employee":
            emp += amount
        elif r.get("arms_length") == "Y" and r.get("in_canada") == "Y":
            con += amount
    out = {"employee_sred_wages": str(q2(emp)), "contractor_sred_amount": str(q2(con))}
    rates = config.rates(cfg) or {}
    if {"itc_rate", "proxy_rate", "contract_rate"} <= rates.keys():
        est = (emp * (1 + Decimal(str(rates["proxy_rate"]))) + con * Decimal(str(rates["contract_rate"]))) * Decimal(str(rates["itc_rate"]))
        out["itc_estimate"] = str(q2(est))
        out["itc_note"] = "Estimate only: ignores expenditure limits, specified-employee caps and proxy-method salary-base rules."
    return out


def write_checks(path, cfg, roster, summary, ledger, scenario, totals, notes=()) -> None:
    payroll = (cfg.get("payroll") or {}).get("total_wages_earned")
    # Payroll covers employees only; contractor invoices are not payroll.
    roster_total = q2(sum((money(r["wages_earned"]) for r in roster if r["classification"] == "employee"), Decimal("0")))
    lines = [f"# Financial checks ({scenario})", ""]
    if not payroll:
        lines.append("- Payroll reconciliation: NOT RUN (set payroll.total_wages_earned in sred.toml)")
    else:
        expected = q2(Decimal(str(payroll)))
        status = "OK" if abs(expected - roster_total) <= Decimal("0.01") else "MISMATCH"
        lines.append(f"- Payroll reconciliation: {status} (payroll {expected}, employees in roster {roster_total})")
    unconfirmed = [s["person"] for s in summary if _pct(s["confirmed_pct"]) is None]
    lines.append(f"- Unconfirmed percentages: {len(unconfirmed)}" + (f" ({', '.join(unconfirmed)})" if unconfirmed else ""))
    lines.append(f"- Review queue: {sum(e['needs_review'] == 'Y' for e in ledger)} ledger rows need a decision (review_queue.csv)")
    lines += [f"- WARNING: {n}" for n in notes]
    lines += ["", "## Flags", ""]
    lines += [f"- {s['person']}: {s['flags']}" for s in summary if s["flags"]] or ["- none"]
    lines += ["", "## Scenario totals", ""] + [f"- {k}: {v}" for k, v in totals.items()]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(claim_dir: Path, scenario: str | None = None, preliminary: bool = False) -> dict:
    claim_dir = Path(claim_dir)
    cfg = config.load_config(claim_dir / "sred.toml")
    scenario = scenario or (cfg.get("claim") or {}).get("scenario")
    if scenario not in SCENARIOS:
        raise TimeBasisError(f"scenario must be one of {sorted(SCENARIOS)} (pass --scenario or set claim.scenario)")
    fy = config.fiscal_year(cfg)
    act_path = claim_dir / "evidence" / "index" / "activity.csv"
    if not act_path.exists():
        raise TimeBasisError("evidence/index/activity.csv not found: run index.py build first")
    _, rows = activity.read_rows(act_path)
    roster = load_roster(claim_dir / "roster.csv")
    fin = claim_dir / "financials"
    out_dir = claim_dir / "scope" / "preliminary" / scenario if preliminary else fin
    cls = config.classification(cfg)
    ledger = sorted(classify(rows, cls["rules"], _read_csv(fin / "classification_overrides.csv"), cls["review_threshold"]),
                    key=lambda e: (e["date"], e["source"], e["key"]))
    months = monthly(ledger, scenario, config.kind_weights(cfg))
    gaps = [(r["id"], m) for r in roster for m in employed_months(r, fy) if not (months.get((r["id"], m)) or {}).get("evidence_days")]
    gap_rows, gap_leftovers = merge_gaps(_read_csv(fin / "gap_months.csv"), gaps)
    previous = [] if preliminary else _read_csv(fin / "person_summary.csv")
    roster_ids = {r["id"] for r in roster}
    person_leftovers = [p for p in previous if p.get("person") not in roster_ids
                        and ((p.get("confirmed_pct") or "").strip() or (p.get("basis") or "").strip())]
    summary = summarize(roster, months, gap_rows, fy, scenario, previous, use_confirmed=not preliminary)
    _write_csv(out_dir / "activity_ledger.csv", LEDGER_COLUMNS, ledger)
    _write_csv(out_dir / "review_queue.csv", LEDGER_COLUMNS, [e for e in ledger if e["needs_review"] == "Y"])
    gap_set, tb = set(gaps), []
    for r in roster:
        for m in employed_months(r, fy):
            d = months.get((r["id"], m)) or {}
            ev, sd = d.get("evidence_days", 0), d.get("sred_days", 0.0)
            tb.append({"person": r["id"], "month": m, "evidence_days": ev, "sred_days": f"{sd:.2f}",
                       "share": f"{(sd / ev) if ev else 0:.4f}",
                       "by_project": ";".join(f"{p}:{v:.2f}" for p, v in sorted(d.get("by_project", {}).items())),
                       "gap": "Y" if (r["id"], m) in gap_set else "N"})
    _write_csv(out_dir / "time_basis.csv", TIME_BASIS_COLUMNS, tb)
    _write_csv(out_dir / "person_summary.csv", SUMMARY_COLUMNS, summary)
    totals = scenario_totals(roster, summary, cfg)
    (out_dir / f"scenario_{scenario}.json").write_text(json.dumps({"scenario": scenario, **totals}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    unmatched_notes = []
    if not preliminary:
        _write_csv(fin / "gap_months.csv", GAP_COLUMNS, gap_rows)
        for name, columns, rows in (("gap_months_unmatched.csv", GAP_COLUMNS, gap_leftovers),
                                    ("person_summary_unmatched.csv", SUMMARY_COLUMNS, person_leftovers)):
            if rows:
                _write_csv(fin / name, columns, rows)
                unmatched_notes.append(f"{len(rows)} claimant entries no longer match and were kept in {name}: review them")
            elif (fin / name).exists():
                (fin / name).unlink()
        with (fin / "labour_summary.csv").open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh, lineterminator="\n").writerows(labour_summary(roster, summary, load_columns(cfg)))
    write_checks(out_dir / "financial_checks.md", cfg, roster, summary, ledger, scenario, totals, unmatched_notes)
    return {"scenario": scenario, "out_dir": str(out_dir), "people": len(summary),
            "review_queue": sum(e["needs_review"] == "Y" for e in ledger), **totals}
