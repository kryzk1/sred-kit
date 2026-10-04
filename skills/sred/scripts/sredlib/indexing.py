"""Build evidence/index from raw captures."""
from __future__ import annotations

import shutil
from pathlib import Path

from . import activity, config, manifest
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
