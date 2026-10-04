#!/usr/bin/env python3
"""Assemble handoff/ for the accountant.

  handoff.py build --claim DIR

Writes T661-Part2-<P>.md (claim markers stripped, lengths stated), evidence_index.csv (cited markers only),
labour_summary.csv, decision_log.md and, if absent, gaps.md. README.md is written by hand.
Then run: check.py handoff --claim DIR
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import handoff


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--claim", default=".")
    args = p.parse_args(argv)
    try:
        written = handoff.build(Path(args.claim))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for name in written:
        print(f"wrote handoff/{name}")
    print("Next: write handoff/README.md, then run check.py handoff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
