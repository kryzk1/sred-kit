#!/usr/bin/env python3
"""Capture raw evidence before access ends.

  capture.py <github|gitlab|linear|jira|git-log> --claim DIR --source NAME
  capture.py check --claim DIR       one cheap test per source; exit 1 if any fails
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sredlib import config
from sredlib.adapters import CaptureError, Context, adapter_key, get_adapter
from sredlib.http import Http, HttpError

TOOLS = ["github", "gitlab", "linear", "jira", "git-log"]


def check_source(claim: Path, src: dict, http) -> tuple[bool, str]:
    method = src.get("method")
    if method == "api":
        try:
            return True, get_adapter(src.get("tool", "")).check(src, http)
        except (CaptureError, HttpError, KeyError) as exc:
            return False, str(exc)
    if method == "export":
        p = Path(src.get("export_path", ""))
        p = p if p.is_absolute() else Path(claim) / p
        return p.exists(), f"export file {'found' if p.exists() else 'missing'}: {p}"
    if method == "git-log":
        missing = [p for p in src.get("paths", []) if not (Path(claim) / p / ".git").exists()]
        return (not missing), ("all clones found" if not missing else f"not git clones: {', '.join(missing)}")
    if method == "connector":
        return True, "captured by Claude through a connector; nothing to test here"
    return False, f"unknown method {method!r}"


def cmd_check(args) -> int:
    claim = Path(args.claim)
    cfg = config.load_config(claim / "sred.toml")
    ok_all, http = True, Http()
    for src in config.sources(cfg):
        ok, msg = check_source(claim, src, http)
        ok_all = ok_all and ok
        print(f"{'OK  ' if ok else 'FAIL'} {src.get('name')}: {msg}")
    return 0 if ok_all else 1


def cmd_capture(args) -> int:
    claim = Path(args.claim)
    cfg = config.load_config(claim / "sred.toml")
    src = config.source(cfg, args.source)
    if adapter_key(src) != args.tool:
        print(f"ERROR: source {args.source!r} is configured as {adapter_key(src)!r}, not {args.tool!r}", file=sys.stderr)
        return 2
    ctx = Context(claim, src, config.fiscal_year(cfg), tz=config.timezone_of(cfg))
    try:
        counts = get_adapter(args.tool).capture(ctx, Http())
    except (CaptureError, HttpError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"{args.source}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"Raw files are in {ctx.raw_dir}. Keep a backup copy of evidence/raw/ somewhere independent.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tool", choices=TOOLS + ["check"])
    p.add_argument("--claim", default=".")
    p.add_argument("--source")
    args = p.parse_args(argv)
    if args.tool == "check":
        return cmd_check(args)
    if not args.source:
        p.error("--source is required")
    return cmd_capture(args)


if __name__ == "__main__":
    sys.exit(main())
