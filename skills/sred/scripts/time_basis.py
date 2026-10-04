#!/usr/bin/env python3
"""Evidence-day time basis and the accountant's labour summary.

  time_basis.py --claim DIR [--scenario conservative|balanced|maximum] [--preliminary]

Writes financials/ (or scope/preliminary/<scenario>/ with --preliminary). Re-running keeps the claimant's
confirmed_pct, basis and override_reason in person_summary.csv and their entries in gap_months.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import config
from sredlib.timebasis import SCENARIOS, TimeBasisError, run


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--claim", default=".")
    p.add_argument("--scenario", choices=sorted(SCENARIOS))
    p.add_argument("--preliminary", action="store_true", help="rough numbers for Phase 3 scenarios; touches nothing in financials/")
    args = p.parse_args(argv)
    try:
        result = run(Path(args.claim), args.scenario, args.preliminary)
    except (TimeBasisError, config.ConfigError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for k, v in result.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
