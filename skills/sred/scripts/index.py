#!/usr/bin/env python3
"""Build and check evidence/index/activity.csv.

  index.py import   --claim DIR --source NAME [--mapping PRESET_OR_PATH]
  index.py build    --claim DIR       every source -> parts/ -> activity.csv + identities_unmatched.csv
  index.py validate --claim DIR       schema, keys, fiscal-year dates, roster ids, raw paths
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sredlib import config, indexing
from sredlib.adapters import CaptureError
from sredlib.mapping import MappingError

ERRORS = (MappingError, config.ConfigError, FileNotFoundError, CaptureError)


def cmd_import(args) -> int:
    claim = Path(args.claim)
    try:
        cfg = config.load_config(claim / "sred.toml")
        res = indexing.import_source(cfg, claim, args.source, args.mapping)
    except ERRORS as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{args.source}: {len(res.rows)} rows, {res.skipped_outside_fy} outside the fiscal year")
    for kind, n in sorted(Counter(r["kind"] for r in res.rows).items()):
        print(f"  {kind}: {n}")
    unmatched = Counter(r["actor_raw"] for r in res.rows if r["person"].startswith("unmatched:") and r["actor_raw"])
    if unmatched:
        print("Unmatched people (add aliases to roster.csv): " + ", ".join(f"{a} ({n})" for a, n in unmatched.most_common()))
    if res.missing_columns:
        print("Columns named in the mapping but absent from the export: " + ", ".join(res.missing_columns))
    if res.unmapped_columns:
        print("Export columns not used: " + ", ".join(res.unmapped_columns))
    for w in res.warnings:
        print(f"WARNING: {w}")
    for f in res.failures[:20]:
        print(f"FAILED: {f}")
    if len(res.failures) > 20:
        print(f"... and {len(res.failures) - 20} more failures")
    return 0


def cmd_build(args) -> int:
    claim = Path(args.claim)
    try:
        cfg = config.load_config(claim / "sred.toml")
        summary = indexing.build(cfg, claim)
    except ERRORS as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for name, n in summary["sources"].items():
        print(f"{name}: {n} rows")
    print(f"activity.csv: {summary['rows']} rows, {summary['unmatched']} with unmatched people (see identities_unmatched.csv)")
    if summary["no_actor"]:
        print(f"{summary['no_actor']} rows name no person in the source (e.g. unassigned issues); they are kept as evidence but not counted in anyone's time")
    for w in summary["warnings"]:
        print(f"WARNING: {w}")
    return 0


def cmd_validate(args) -> int:
    claim = Path(args.claim)
    problems = indexing.validate(config.load_config(claim / "sred.toml"), claim)
    for p in problems[:50]:
        print(p)
    if len(problems) > 50:
        print(f"... and {len(problems) - 50} more")
    print(f"{len(problems)} problems" if problems else "activity.csv is valid")
    return 1 if problems else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="convert one export file using a mapping")
    imp.add_argument("--claim", default=".")
    imp.add_argument("--source", required=True)
    imp.add_argument("--mapping")
    imp.set_defaults(func=cmd_import)
    for name, func in (("build", cmd_build), ("validate", cmd_validate)):
        sp = sub.add_parser(name)
        sp.add_argument("--claim", default=".")
        sp.set_defaults(func=func)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
