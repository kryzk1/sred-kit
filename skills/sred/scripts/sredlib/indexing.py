"""Build evidence/index from raw captures."""
from __future__ import annotations

import csv
import shutil
from pathlib import Path

from . import activity, config, manifest
from .adapters import Context, adapter_key, get_adapter
from .mapping import ImportResult, import_export, load_mapping
from .roster import Resolver, load_roster


def parts_dir(claim_dir: Path) -> Path:
    return Path(claim_dir) / "evidence" / "index" / "parts"


def resolver_for(cfg: dict, claim_dir: Path) -> Resolver:
    roster_path = Path(claim_dir) / "roster.csv"
    roster = load_roster(roster_path) if roster_path.exists() else []
    return Resolver(roster, extra_bots=(cfg.get("identity") or {}).get("bots", []))


def stage_export(claim_dir: Path, src: dict) -> Path:
    """Raw-first: make sure the export lives under evidence/raw/<name>/ before converting it."""
    claim_dir = Path(claim_dir)
    if not src.get("export_path"):
        raise config.ConfigError(f"source {src['name']!r} has no export_path")
    given = Path(src["export_path"])
    given = given if given.is_absolute() else claim_dir / given
    if not given.exists():
        raise FileNotFoundError(f"export file not found: {given}")
    raw_dir = claim_dir / "evidence" / "raw" / src["name"]
    if raw_dir.resolve() in given.resolve().parents:
        return given
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = raw_dir / given.name
    if given.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(given, target)
    else:
        shutil.copy2(given, target)
    return target


def import_source(cfg: dict, claim_dir: Path, name: str, mapping_spec: str | None = None) -> ImportResult:
    claim_dir = Path(claim_dir)
    src = config.source(cfg, name)
    staged = stage_export(claim_dir, src)
    spec = mapping_spec or src.get("mapping")
    if not spec:
        raise config.ConfigError(f'source {name!r} needs mapping = "<preset or path>"')
    result = import_export(load_mapping(spec, claim_dir), staged, source=name, resolver=resolver_for(cfg, claim_dir),
                           regexes=config.issue_key_regexes(cfg), claim_dir=claim_dir, fy=config.fiscal_year(cfg),
                           tz=config.timezone_of(cfg))
    files = [staged] if staged.is_file() else sorted(p for p in staged.rglob("*") if p.is_file())
    dates = sorted(r["date"] for r in result.rows)
    manifest.record(claim_dir, name, method="export", files=files,
                    counts={"rows": len(result.rows), "skipped_outside_fy": result.skipped_outside_fy, "failures": len(result.failures)},
                    date_range=(dates[0], dates[-1]) if dates else None, notes=result.warnings)
    activity.write_rows(parts_dir(claim_dir) / f"{name}.csv", result.rows)
    return result


UNMATCHED_COLUMNS = ["source", "actor_raw", "rows", "first_date", "last_date", "sample_key"]


def connector_rows(claim_dir: Path, src: dict, resolver: Resolver) -> list[dict]:
    path = Path(claim_dir) / "evidence" / "raw" / src["name"] / "rows.csv"
    if not path.exists():
        raise FileNotFoundError(f"connector source {src['name']!r}: expected Claude-written rows at {path}")
    _, rows = activity.read_rows(path)
    for r in rows:
        r["source"] = src["name"]
        if r.get("actor_raw"):
            r["person"] = resolver.resolve(src.get("tool", src["name"]), r["actor_raw"])
    return rows


def write_unmatched(path: Path, rows: list[dict]) -> None:
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r["person"].startswith("unmatched:") and r["actor_raw"]:
            groups.setdefault((r["source"], r["actor_raw"]), []).append(r)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(UNMATCHED_COLUMNS)
        for (source, actor), items in sorted(groups.items()):
            dates = sorted(i["date"] for i in items)
            writer.writerow([source, actor, len(items), dates[0], dates[-1], sorted(i["key"] for i in items)[0]])


def build(cfg: dict, claim_dir: Path) -> dict:
    claim_dir = Path(claim_dir)
    fy, tz = config.fiscal_year(cfg), config.timezone_of(cfg)
    resolver = resolver_for(cfg, claim_dir)
    regexes = tuple(config.issue_key_regexes(cfg))
    summary: dict = {"sources": {}, "warnings": []}
    all_rows: list[dict] = []
    for src in config.sources(cfg):
        name, method = src.get("name"), src.get("method")
        if method in ("api", "git-log"):
            ctx = Context(claim_dir, src, fy, resolver, regexes, tz)
            if not ctx.raw_dir.exists() or not any(ctx.raw_dir.iterdir()):
                raise FileNotFoundError(f"no raw files for source {name!r}: run `capture.py {adapter_key(src)} --source {name}` first")
            rows = get_adapter(adapter_key(src)).normalize(ctx)
            activity.write_rows(parts_dir(claim_dir) / f"{name}.csv", rows)
        elif method == "export":
            result = import_source(cfg, claim_dir, name)
            rows = result.rows
            summary["warnings"] += [f"{name}: {w}" for w in result.warnings] + [f"{name}: {f}" for f in result.failures[:5]]
        elif method == "connector":
            rows = connector_rows(claim_dir, src, resolver)
            activity.write_rows(parts_dir(claim_dir) / f"{name}.csv", rows)
        else:
            raise config.ConfigError(f"source {name!r}: unknown method {method!r}")
        summary["sources"][name] = len(rows)
        all_rows += rows
    index_dir = claim_dir / "evidence" / "index"
    activity.write_rows(index_dir / "activity.csv", all_rows)
    write_unmatched(index_dir / "identities_unmatched.csv", all_rows)
    summary["rows"] = len(all_rows)
    summary["unmatched"] = sum(1 for r in all_rows if r["person"].startswith("unmatched:") and r["actor_raw"])
    summary["no_actor"] = sum(1 for r in all_rows if r["person"].startswith("unmatched:") and not r["actor_raw"])
    return summary


def validate(cfg: dict, claim_dir: Path) -> list[str]:
    claim_dir = Path(claim_dir)
    path = claim_dir / "evidence" / "index" / "activity.csv"
    if not path.exists():
        return ["evidence/index/activity.csv is missing: run index.py build"]
    start, end = config.fiscal_year(cfg)
    roster_path = claim_dir / "roster.csv"
    ids = {r["id"] for r in load_roster(roster_path)} if roster_path.exists() else None
    header, rows = activity.read_rows(path)
    return activity.validate_rows(rows, header, start, end, claim_dir, ids)
