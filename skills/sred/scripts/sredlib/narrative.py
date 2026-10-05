"""Parse a project narrative (draft/<P>/narrative.md) and check it mechanically."""
from __future__ import annotations

import re
import textwrap
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import config

LINES = ("242", "244", "246")
MARKER_RE = re.compile(r"\s?\[C\d+\]")
MARKER_ID_RE = re.compile(r"\[(C\d+)\]")
HEADING_RE = re.compile(r"(?m)^(#{1,4})\s+(.*?)\s*$")
ITEM_RE = re.compile(r"(?m)^\s*-\s*([^:\n]+?)\s*:\s*(.*)$")
SEVERITY_LEVEL = {"hard": "error", "high": "warning", "med": "warning", "low": "info", "soft": "info"}
PATTERNS_PATH = Path(__file__).resolve().parent.parent.parent / "references" / "do-not-patterns.toml"
PLAIN_TEXT_RE = re.compile(r"(?m)^\s*([-*•]|\d+[.)])\s|\*\*|^#|\||\t")
NUMBER_RE = re.compile(r"(?<![\w-])\d[\d,.]*%?")
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MONTH_YEAR_RE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b")
CONTRACTOR_RE = re.compile(r"\b(sub)?contract(or|ors|ed|ing)\b", re.I)


@dataclass
class Narrative:
    project: str = ""
    title: str = ""
    section_a: dict = field(default_factory=dict)
    lines: dict = field(default_factory=dict)
    section_c: dict = field(default_factory=dict)


@dataclass
class Finding:
    severity: str
    rule: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.upper():7} {self.rule:8} [{self.where}] {self.message}"


def _items(body: str) -> dict:
    return {m.group(1).strip(): m.group(2).strip() for m in ITEM_RE.finditer(body)}


def parse_narrative(text: str) -> Narrative:
    n = Narrative()
    heads = list(HEADING_RE.finditer(text))
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        level, title = len(h.group(1)), h.group(2)
        line_m = re.search(r"\bLine\s+(24[246])\b", title)
        if level == 1 and not n.project:
            m = re.match(r"(\S+?):\s*(.*)", title)
            n.project, n.title = (m.group(1), m.group(2)) if m else ("", title)
        elif line_m:
            n.lines[line_m.group(1)] = "\n".join(l for l in body.strip().splitlines() if l.strip() != "---").strip()
        elif re.search(r"\bSection A\b", title):
            n.section_a = {k[:3]: v for k, v in _items(body).items() if re.match(r"\d{3}", k)}
        elif re.search(r"\bSection C\b", title):
            n.section_c = {k.lower(): v for k, v in _items(body).items()}
    return n


def strip_markers(text: str) -> str:
    return MARKER_RE.sub("", text or "")


def word_count(text: str) -> int:
    return len([t for t in strip_markers(text).split() if t != "---"])


def line_count(text: str, width: int = 78) -> int:
    paras = [p for p in re.split(r"\n\s*\n", strip_markers(text).strip()) if p.strip()]
    return sum(len(textwrap.wrap(" ".join(p.split()), width)) for p in paras) + max(len(paras) - 1, 0)


def load_patterns(path: Path | None = None) -> list[dict]:
    return tomllib.loads(Path(path or PATTERNS_PATH).read_text(encoding="utf-8")).get("pattern", [])


def yes(value: str) -> bool:
    return (value or "").strip().lower() in ("yes", "y", "x", "true")


def _date(value: str):
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        return None


def check_narrative(n: Narrative, evidence: list[dict], cfg: dict, patterns: list[dict]) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    counts: dict[str, tuple[int, int]] = {}
    lim = config.limits(cfg)
    start, end = config.fiscal_year(cfg)
    claim = cfg.get("claim") or {}

    def add(severity, rule, where, message):
        findings.append(Finding(severity, rule, where, message))

    # Length, plain text, and numbers that need a claim marker
    for line in LINES:
        text = n.lines.get(line, "")
        if not text:
            add("error", "STRUCT", line, f"Line {line} is missing or empty")
            continue
        words, lines_ = word_count(text), line_count(text, lim["line_width"])
        counts[line] = (words, lines_)
        wmax, lmax = lim["words"][line], lim["lines"][line]
        w_sev, l_sev = ("error", "warning") if lim["mode"] == "words" else ("warning", "error")
        if words > wmax:
            add(w_sev, "M-L01", line, f"{words} words, limit {wmax}")
        elif words >= wmax - 5:
            add("info", "M-L03", line, f"{words} words leaves less than 5 words of headroom")
        if lines_ > lmax:
            add(l_sev, "M-L02", line, f"{lines_} lines at {lim['line_width']} characters, budget {lmax}")
        if PLAIN_TEXT_RE.search(text):
            add("warning", "M-L04", line, "plain text only: no bullets, bold, headings, tables or tabs")
        for sentence in SENTENCE_RE.split(text):
            nums = [x for x in NUMBER_RE.findall(strip_markers(sentence)) if not YEAR_RE.match(x.rstrip(".,%"))]
            if nums and not MARKER_ID_RE.search(sentence):
                add("warning", "M-L14", line, f"number without a claim marker: {nums[0]!r} in {sentence.strip()[:80]!r}")
        late = [d for d in ISO_DATE_RE.findall(text) if _date(d) and _date(d) > end]
        late += [f"{mon} {yr}" for mon, yr in MONTH_YEAR_RE.findall(text) if (int(yr), MONTHS.index(mon) + 1) > (end.year, end.month)]
        if late:
            add("warning", "M-L12", line, "work after the fiscal year end belongs to next year's claim: " + ", ".join(late))

    # Claim markers resolve to verified evidence rows
    rows = {r.get("claim_id", ""): r for r in evidence}
    for line in LINES:
        for cid in MARKER_ID_RE.findall(n.lines.get(line, "")):
            row = rows.get(cid)
            if row is None:
                add("error", "EVIDENCE", line, f"marker [{cid}] has no row in evidence_table.csv")
            elif (row.get("verified") or "").strip().upper() != "Y":
                add("error", "EVIDENCE", line, f"marker [{cid}] is not verified against raw evidence")

    # Mechanical do-not patterns
    texts = {**{line: strip_markers(n.lines.get(line, "")) for line in LINES}, "title": n.section_a.get("200", "")}
    for p in patterns:
        rx = re.compile(p["regex"], (0 if p.get("case_sensitive") else re.I) | re.M)
        excl = re.compile(p["exclude"], re.I) if p.get("exclude") else None
        for scope in p.get("scope", list(LINES)):
            body = texts.get(scope, "")
            hits = [m for m in rx.finditer(body) if not (excl and excl.search(body[max(0, m.start() - 60): m.end() + 60]))]
            if hits:
                sample = ", ".join(dict.fromkeys(h.group(0) for h in hits[:3]))
                add(SEVERITY_LEVEL[p.get("severity", "med")], p["id"], scope, f"{len(hits)}x {sample!r}: {p.get('hint', '')}")

    # Section A
    a = n.section_a
    for k, label in (("200", "project title"), ("202", "start date"), ("204", "completion date"), ("206", "field of science code")):
        if not a.get(k):
            add("error", "STRUCT", "A", f"Line {k} ({label}) is missing")
    cont, first = yes(a.get("208", "")), yes(a.get("210", ""))
    if cont == first:
        add("error", "M-L06", "A", "exactly one of Line 208 (continuation) and Line 210 (first claim) must be marked")
    prior_titles = claim.get("prior_titles") or []
    if cont and prior_titles and a.get("200", "") not in prior_titles:
        add("error", "M-L05", "A", "a continuing project keeps its previously filed title verbatim: " + " | ".join(prior_titles))
    d202, d204 = _date(a.get("202", "")), _date(a.get("204", ""))
    if a.get("202") and d202 is None:
        add("warning", "M-L10", "A", "Line 202 must be YYYY-MM-DD")
    if a.get("204") and d204 is None:
        add("warning", "M-L10", "A", "Line 204 must be YYYY-MM-DD")
    if a.get("206") and not re.fullmatch(r"\d\.\d{2}\.\d{2}", a["206"]):
        add("warning", "M-L10", "A", "Line 206 must look like 2.02.09")
    prior_codes = claim.get("field_codes") or []
    if a.get("206") and prior_codes and a["206"] not in prior_codes:
        add("info", "M-L10", "A", "field code differs from the prior filing; keep it unless the technology changed")
    if d202:
        if d202 == start:
            add("warning", "M-L07", "A", "start date equals the fiscal year start; use the earliest evidenced hypothesis")
        if d202 > end:
            add("error", "STRUCT", "A", "start date is after the fiscal year end")
        if d202 < start and not cont:
            add("error", "STRUCT", "A", "a start date before the fiscal year requires Line 208 (continuation)")
        if first:
            for prior in claim.get("prior_projects") or []:
                pend = prior.get("end")
                if isinstance(pend, date) and 0 < (d202 - pend).days < 90:
                    add("warning", "M-L08", "A", f"starts {(d202 - pend).days} days after prior project {prior.get('title', '')!r} ended: prepare a demarcation note")

    # Contractors named in Section C must appear in Line 244
    contractors = n.section_c.get("contractors", "").strip().lower()
    if contractors not in ("", "none", "n/a") and not CONTRACTOR_RE.search(n.lines.get("244", "")):
        add("warning", "M-L11", "244", "contractors are listed in Section C but Line 244 never says what contractors did")
    return findings, counts
