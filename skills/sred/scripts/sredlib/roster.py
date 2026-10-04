"""Roster loading and identity resolution across tools."""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROSTER_COLUMNS = [
    "id", "name", "classification", "company", "title", "start", "end", "in_canada", "specified_employee",
    "aliases", "paid_hours", "wages_paid", "wages_earned", "bonus", "taxable_benefits", "pay_in_lieu",
    "arms_length", "contract_provided", "sred_in_contract", "street", "city", "province", "postal", "country",
]
DEFAULT_BOT_RE = re.compile(r"(\[bot\]$|^(dependabot|renovate|github-actions|slackbot|vercel|codecov)\b|[-_]bot$)", re.I)
ANGLE_RE = re.compile(r"^(.*?)\s*<([^<>@\s]+@[^<>\s]+)>$")


def load_roster(path: Path) -> list[dict]:
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k in ROSTER_COLUMNS:
            r[k] = (r.get(k) or "").strip()
    return rows


def parse_aliases(text: str) -> list[tuple[str, str]]:
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        tool, value = part.split(":", 1)
        out.append((tool.strip().lower(), value.strip().lower()))
    return out


class Resolver:
    """Maps a tool's actor (handle, id, email, display name) to a roster id."""

    def __init__(self, roster: list[dict], extra_bots: list[str] | None = None):
        self.index: dict[tuple[str, str], str] = {}
        self.email: dict[str, str] = {}
        self.names: dict[str, str] = {}
        for r in roster:
            pid = r["id"]
            for tool, value in parse_aliases(r.get("aliases", "")):
                if tool == "email":
                    self.email[value] = pid
                else:
                    self.index[(tool, value)] = pid
            if r.get("name"):
                self.names[r["name"].strip().lower()] = pid
        self.extra_bots = {b.lower() for b in (extra_bots or [])}

    def is_bot(self, actor: str) -> bool:
        a = (actor or "").strip()
        return bool(a) and (a.lower() in self.extra_bots or bool(DEFAULT_BOT_RE.search(a)))

    def resolve(self, tool: str, actor: str, email: str = "", name: str = "") -> str:
        actor, email, name = (actor or "").strip(), (email or "").strip().lower(), (name or "").strip()
        m = ANGLE_RE.match(actor)
        if m:
            name = name or m.group(1).strip()
            email = email or m.group(2).lower()
            actor = m.group(1).strip() or email
        if not actor and not email and not name:
            return "unmatched:"
        if self.is_bot(actor) or (name and self.is_bot(name)):
            return "bot"
        key = (tool.lower(), actor.lower())
        if key in self.index:
            return self.index[key]
        if email and email in self.email:
            return self.email[email]
        if "@" in actor and actor.lower() in self.email:
            return self.email[actor.lower()]
        for candidate in (name, actor):
            if candidate and candidate.lower() in self.names:
                return self.names[candidate.lower()]
        return f"unmatched:{actor or email or name}"
