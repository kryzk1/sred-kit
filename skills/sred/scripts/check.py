#!/usr/bin/env python3
"""Checks that gate each phase.

  check.py setup --claim DIR [--phase N]     what onboarding still needs; exit 1 if anything blocks phase N
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import setupcheck


def cmd_setup(args) -> int:
    claim = Path(args.claim)
    missing, info = setupcheck.check_setup(claim)
    phase = args.phase or setupcheck.current_phase(claim)
    for line in info:
        print(line)
    for m in missing:
        print(m)
    blocking = [m for m in missing if m.phase <= phase]
    print(f"{len(missing)} missing; {len(blocking)} block phase {phase}." if missing else "Setup complete: nothing missing.")
    return 1 if blocking else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="what onboarding still needs")
    s.add_argument("--claim", default=".")
    s.add_argument("--phase", type=int)
    s.set_defaults(func=cmd_setup)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
