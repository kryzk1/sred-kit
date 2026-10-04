#!/usr/bin/env python3
"""Checks that gate each phase.

  check.py setup --claim DIR [--phase N]           what onboarding still needs; exit 1 if anything blocks phase N
  check.py narrative PATH [--claim DIR] [--evidence CSV] [--patterns TOML]
                                                   lengths, do-not patterns, claim markers, Section A; exit 1 on errors
  check.py handoff --claim DIR                     handoff/ complete and consistent with scope and financials
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sredlib import config, handoff, narrative, setupcheck

ORDER = {"error": 0, "warning": 1, "info": 2}


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


def print_findings(findings) -> int:
    for f in sorted(findings, key=lambda f: (ORDER[f.severity], f.where, f.rule)):
        print(f)
    errors = sum(f.severity == "error" for f in findings)
    print(f"{errors} errors, {sum(f.severity == 'warning' for f in findings)} warnings")
    return 1 if errors else 0


def cmd_narrative(args) -> int:
    path = Path(args.narrative)
    claim = Path(args.claim) if args.claim else path.resolve().parents[2]
    cfg = config.load_config(claim / "sred.toml")
    ev_path = Path(args.evidence) if args.evidence else path.parent / "evidence_table.csv"
    evidence = list(csv.DictReader(ev_path.open(newline="", encoding="utf-8"))) if ev_path.exists() else []
    n = narrative.parse_narrative(path.read_text(encoding="utf-8"))
    findings, counts = narrative.check_narrative(n, evidence, cfg, narrative.load_patterns(args.patterns))
    lim = config.limits(cfg)
    print(f"{n.project or path}: limit mode = {lim['mode']}")
    for line, (w, l) in counts.items():
        print(f"  Line {line}: {w}/{lim['words'][line]} words, {l}/{lim['lines'][line]} lines")
    return print_findings(findings)


def cmd_handoff(args) -> int:
    return print_findings(handoff.check(Path(args.claim)))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup", help="what onboarding still needs")
    s.add_argument("--claim", default=".")
    s.add_argument("--phase", type=int)
    s.set_defaults(func=cmd_setup)
    nar = sub.add_parser("narrative", help="check one draft/<P>/narrative.md")
    nar.add_argument("narrative")
    nar.add_argument("--claim")
    nar.add_argument("--evidence")
    nar.add_argument("--patterns")
    nar.set_defaults(func=cmd_narrative)
    h = sub.add_parser("handoff", help="check handoff/ for completeness and consistency")
    h.add_argument("--claim", default=".")
    h.set_defaults(func=cmd_handoff)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
