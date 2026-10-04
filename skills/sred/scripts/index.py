#!/usr/bin/env python3
"""Build and check evidence/index/activity.csv.

  index.py import   --claim DIR --source NAME [--mapping PRESET_OR_PATH]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from sredlib import config, indexing
from sredlib.mapping import MappingError


def cmd_import(args) -> int:
    claim = Path(args.claim)
    try:
        cfg = config.load_config(claim / "sred.toml")
        res = indexing.import_source(cfg, claim, args.source, args.mapping)
    except (MappingError, config.ConfigError, FileNotFoundError) as exc:
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


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="convert one export file using a mapping")
    imp.add_argument("--claim", default=".")
    imp.add_argument("--source", required=True)
    imp.add_argument("--mapping")
    imp.set_defaults(func=cmd_import)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
