"""The shared activity table that every phase after capture reads."""
from __future__ import annotations

import csv
import re
from datetime import date, datetime, timezone
from pathlib import Path

from .dates import iso

COLUMNS = ["source", "key", "kind", "person", "actor_raw", "date", "timestamp", "container", "tags", "paths",
           "title", "excerpt", "refs", "url", "raw_path", "weight"]
KINDS = {"commit", "pr_opened", "pr_merged", "pr_review", "pr_comment", "issue_created", "issue_state_change",
         "issue_resolved", "issue_assigned", "issue_comment", "chat_message", "meeting", "doc_edit"}
WEIGHTS = {"verbatim", "summary"}
EXCERPT_MAX = 500
PATHS_MAX = 50
TRUNC = "…[truncated]"
PR_URL_RE = re.compile(r"https?://(?:www\.)?github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)")
MR_URL_RE = re.compile(r"https?://[\w.-]+/([\w.-]+(?:/[\w.-]+)+)/-/merge_requests/(\d+)")
PERSON_RE = re.compile(r"[\w.-]+")


def truncate(text: str, limit: int = EXCERPT_MAX) -> str:
    text = (text or "").replace("\r\n", "\n")
    return text if len(text) <= limit else text[:limit] + TRUNC


def join(values) -> str:
    out: list[str] = []
    for v in values:
        v = (v or "").strip()
        if v and v not in out:
            out.append(v)
    return ";".join(out)


def split(value: str) -> list[str]:
    return [v for v in (value or "").split(";") if v]


def first_line(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()[:300]
    return ""


def extract_refs(text: str, regexes: list[str], own_key: str = "") -> list[str]:
    """Issue keys (configured regexes, no capture groups needed) plus GitHub PR and GitLab MR URLs."""
    text = text or ""
    found: list[str] = []
    for rx in regexes:
        found += [m.group(0) for m in re.finditer(rx, text)]
    found += [f"{repo}#{num}" for repo, num in PR_URL_RE.findall(text)]
    found += [f"{path}!{num}" for path, num in MR_URL_RE.findall(text)]
    return [f for f in dict.fromkeys(found) if f and f != own_key]


def local_date(ts: datetime, tz=None) -> date:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(tz or timezone.utc).date()


def in_window(ts: datetime, start: date, end: date, tz=None) -> bool:
    return start <= local_date(ts, tz) <= end


def make_row(*, source, key, kind, person, actor_raw, ts: datetime, container="", tags=(), paths=(), title="",
             excerpt="", refs=(), url="", raw_path="", weight="verbatim", tz=None) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}")
    if weight not in WEIGHTS:
        raise ValueError(f"unknown weight {weight!r}")
    paths = [p for p in paths if p]
    path_str = join(paths[:PATHS_MAX])
    if len(paths) > PATHS_MAX:
        path_str += ";" + TRUNC
    return {
        "source": source, "key": key, "kind": kind, "person": person, "actor_raw": actor_raw or "",
        "date": local_date(ts, tz).isoformat(), "timestamp": iso(ts), "container": container or "",
        "tags": join(tags), "paths": path_str, "title": first_line(title), "excerpt": truncate(excerpt),
        "refs": join(refs), "url": url or "", "raw_path": raw_path, "weight": weight,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r["timestamp"], r["source"], r["key"]))
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in ordered:
            writer.writerow({c: r.get(c, "") for c in COLUMNS})


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def validate_rows(rows: list[dict], header: list[str], start: date, end: date, claim_dir: Path,
                  roster_ids: set[str] | None = None) -> list[str]:
    if header != COLUMNS:
        return ["columns must be exactly: " + ",".join(COLUMNS)]
    problems: list[str] = []
    seen: set[tuple[str, str]] = set()
    for i, r in enumerate(rows, start=2):
        where = f"line {i} ({r['source']}:{r['key']})"
        if not r["source"] or not r["key"]:
            problems.append(f"{where}: source and key are required")
        if (r["source"], r["key"]) in seen:
            problems.append(f"{where}: duplicate source+key")
        seen.add((r["source"], r["key"]))
        if r["kind"] not in KINDS:
            problems.append(f"{where}: unknown kind {r['kind']!r}")
        if r["weight"] not in WEIGHTS:
            problems.append(f"{where}: weight must be 'verbatim' or 'summary'")
        person = r["person"]
        if person != "bot" and not person.startswith("unmatched:"):
            if not PERSON_RE.fullmatch(person or ""):
                problems.append(f"{where}: person must be a roster id, 'bot' or 'unmatched:<raw>'")
            elif roster_ids is not None and person not in roster_ids:
                problems.append(f"{where}: person {person!r} is not in roster.csv")
        try:
            d = date.fromisoformat(r["date"])
            if not start <= d <= end:
                problems.append(f"{where}: date {d} is outside the fiscal year {start}..{end}")
        except ValueError:
            problems.append(f"{where}: date must be YYYY-MM-DD")
        if not r["raw_path"] or not (Path(claim_dir) / r["raw_path"]).exists():
            problems.append(f"{where}: raw_path {r['raw_path']!r} does not exist")
    return problems
