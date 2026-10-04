"""Convert a tool's export file into activity rows using a small TOML mapping."""
from __future__ import annotations

import csv
import json
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import activity
from .dates import parse_datetime
from .roster import Resolver

PRESET_DIR = Path(__file__).resolve().parent.parent.parent / "mappings"
FORMATS = {"csv", "json", "slack-export"}


class MappingError(ValueError):
    pass


@dataclass
class ImportResult:
    rows: list[dict] = field(default_factory=list)
    unmapped_columns: list[str] = field(default_factory=list)
    missing_columns: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_outside_fy: int = 0


def load_mapping(spec: str, claim_dir: Path) -> dict:
    path = Path(spec)
    if path.suffix != ".toml":
        path = PRESET_DIR / f"{spec}.toml"
    elif not path.is_absolute():
        path = Path(claim_dir) / path
    if not path.exists():
        presets = sorted(p.stem for p in PRESET_DIR.glob("*.toml"))
        raise MappingError(f"mapping {spec!r} not found; presets: {', '.join(presets)}")
    mapping = tomllib.loads(path.read_text(encoding="utf-8"))
    mapping["_path"] = str(path)
    _check_structure(mapping)
    return mapping


def _check_structure(m: dict) -> None:
    fmt = m.get("format", "csv")
    if fmt not in FORMATS:
        raise MappingError(f"format must be one of {sorted(FORMATS)}")
    if fmt == "slack-export":
        return
    for req in ("tool", "key", "events"):
        if not m.get(req):
            raise MappingError(f"mapping is missing {req!r}")
    for ev in m["events"]:
        if ev.get("kind") not in activity.KINDS:
            raise MappingError(f"event kind {ev.get('kind')!r} is not a known activity kind")
        if ev.get("repeat"):
            if "date" not in (ev.get("split_fields") or []):
                raise MappingError("repeat events need split_fields including 'date'")
        elif not ev.get("date"):
            raise MappingError(f"event {ev['kind']!r} needs a 'date' column")


class CsvRecord:
    def __init__(self, header: list[str], values: list[str]):
        self.pairs = list(zip(header, values))

    def get(self, name: str) -> str:
        for h, v in self.pairs:
            if h == name and v.strip():
                return v.strip()
        return ""

    def get_all(self, name: str) -> list[str]:
        return [v.strip() for h, v in self.pairs if h == name and v.strip()]


class JsonRecord:
    """Dotted paths into one JSON record; `a.b[].c` maps over the list at `b`."""

    def __init__(self, data):
        self.data = data

    def _walk(self, node, parts):
        if not parts:
            return node
        head, rest = parts[0], parts[1:]
        if head.endswith("[]"):
            items = node.get(head[:-2]) if isinstance(node, dict) else None
            if not isinstance(items, list):
                return []
            out = []
            for item in items:
                v = self._walk(item, rest)
                out.extend(v if isinstance(v, list) else [v])
            return out
        return self._walk(node.get(head), rest) if isinstance(node, dict) else None

    def get_all(self, name: str) -> list[str]:
        v = self._walk(self.data, name.split("."))
        values = v if isinstance(v, list) else [v]
        return [str(x).strip() for x in values if x is not None and not isinstance(x, (dict, list)) and str(x).strip()]

    def get(self, name: str) -> str:
        values = self.get_all(name)
        return values[0] if values else ""


def _first(rec, spec) -> str:
    if not spec:
        return ""
    for name in ([spec] if isinstance(spec, str) else spec):
        v = rec.get(name)
        if v:
            return v
    return ""


def _load_csv(path: Path) -> tuple[list[str], list[CsvRecord]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = [h.strip() for h in next(reader, [])]
        records = [CsvRecord(header, row) for row in reader if any(c.strip() for c in row)]
    return header, records


def _load_json(path: Path, records_path: str) -> list[JsonRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if records_path:
        for part in records_path.split("."):
            data = data.get(part, []) if isinstance(data, dict) else []
    if not isinstance(data, list):
        raise MappingError(f"records path {records_path!r} does not point at a list")
    return [JsonRecord(item) for item in data]


def _referenced(m: dict) -> list[str]:
    names: list[str] = []

    def add(spec):
        if isinstance(spec, str) and spec:
            names.append(spec)
        elif isinstance(spec, list):
            names.extend(s for s in spec if s)

    for k in ("key", "container", "title", "url"):
        add(m.get(k))
    add(m.get("tags", []))
    for ev in m["events"]:
        for k in ("date", "actor", "actor_email", "actor_name", "excerpt", "repeat"):
            add(ev.get(k))
        if ev.get("when"):
            add(ev["when"].get("field"))
    return list(dict.fromkeys(names))


def _event_items(ev: dict, rec) -> list[tuple[str, dict]]:
    if ev.get("repeat"):
        fields_ = ev["split_fields"]
        items = []
        for i, value in enumerate(rec.get_all(ev["repeat"]), start=1):
            parts = value.split(ev.get("split", ";"), len(fields_) - 1)
            items.append((f":{ev['kind']}:{i}", dict(zip(fields_, parts))))
        return items
    return [(ev.get("key_suffix", f":{ev['kind']}"), {
        "date": rec.get(ev["date"]),
        "actor": rec.get(ev["actor"]) if ev.get("actor") else "",
        "actor_email": rec.get(ev["actor_email"]) if ev.get("actor_email") else "",
        "actor_name": rec.get(ev["actor_name"]) if ev.get("actor_name") else "",
        "excerpt": rec.get(ev["excerpt"]) if ev.get("excerpt") else "",
    })]


def _clean_actor(ev: dict, actor: str) -> str:
    actor = (actor or "").strip()
    if ev.get("actor_strip"):
        actor = actor.strip(ev["actor_strip"]).strip()
    if ev.get("actor_split"):
        actor = actor.split(ev["actor_split"])[0].strip()
    return actor


def import_export(mapping: dict, export_path: Path, *, source: str, resolver: Resolver, regexes: list[str],
                  claim_dir: Path, fy: tuple[date, date], tz=None) -> ImportResult:
    fmt = mapping.get("format", "csv")
    if fmt == "slack-export":
        from .slack_export import import_slack

        return import_slack(export_path, source=source, resolver=resolver, regexes=regexes, claim_dir=claim_dir, fy=fy, tz=tz)
    result = ImportResult()
    if not mapping.get("verified", False):
        result.warnings.append(f"mapping {Path(mapping['_path']).name} has not been verified against a real export: "
                               "check the column report and the first rows before relying on it")
    if fmt == "csv":
        header, records = _load_csv(export_path)
        referenced = _referenced(mapping)
        result.missing_columns = [c for c in referenced if c not in header]
        result.unmapped_columns = [c for c in dict.fromkeys(header) if c and c not in referenced]
        required = [mapping["key"]] + [ev["date"] for ev in mapping["events"] if not ev.get("repeat")]
        fatal = [c for c in dict.fromkeys(required) if c not in header]
        if fatal:
            raise MappingError(f"export is missing required columns: {', '.join(fatal)}")
    else:
        records = _load_json(export_path, mapping.get("records", ""))
    raw_path = str(Path(export_path).resolve().relative_to(Path(claim_dir).resolve()))
    formats = mapping.get("date_formats", ["iso"])
    start, end = fy
    seen: set[str] = set()
    for n, rec in enumerate(records, start=1):
        base = rec.get(mapping["key"])
        if not base:
            result.failures.append(f"record {n}: empty key {mapping['key']!r}")
            continue
        container, title, url = _first(rec, mapping.get("container")), _first(rec, mapping.get("title")), _first(rec, mapping.get("url"))
        tags = [t for col in mapping.get("tags", []) for t in rec.get_all(col)]
        for ev in mapping["events"]:
            when = ev.get("when")
            if when and rec.get(when["field"]) != when["equals"]:
                continue
            for suffix, f in _event_items(ev, rec):
                if not (f.get("date") or "").strip():
                    continue
                key = f"{base}{suffix}"
                try:
                    ts = parse_datetime(f["date"], formats)
                except ValueError as exc:
                    result.failures.append(f"record {n} ({key}): {exc}")
                    continue
                if not activity.in_window(ts, start, end, tz):
                    result.skipped_outside_fy += 1
                    continue
                if key in seen:
                    result.failures.append(f"record {n}: duplicate key {key!r} skipped")
                    continue
                seen.add(key)
                actor = _clean_actor(ev, f.get("actor", ""))
                excerpt = (f.get("excerpt") or "").strip()
                result.rows.append(activity.make_row(
                    source=source, key=key, kind=ev["kind"],
                    person=resolver.resolve(mapping["tool"], actor, email=f.get("actor_email", ""), name=f.get("actor_name", "")),
                    actor_raw=actor, ts=ts, container=container, tags=tags, title=title, excerpt=excerpt,
                    refs=activity.extract_refs(f"{title}\n{excerpt}", regexes, own_key=base), url=url,
                    raw_path=raw_path, weight=mapping.get("weight", "verbatim"), tz=tz,
                ))
    return result
