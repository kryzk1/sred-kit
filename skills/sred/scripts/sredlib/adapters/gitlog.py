"""Commits from local clones with `git log --all` (works for any git host)."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context

FORMAT = "%x1e%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b%x1f"


def _clones(ctx: Context) -> list[Path]:
    paths = ctx.source.get("paths") or []
    if not paths:
        raise CaptureError('git-log source needs paths = ["../clones/repo", ...]')
    out = []
    for p in paths:
        path = Path(p) if Path(p).is_absolute() else Path(ctx.claim_dir) / p
        if not (path / ".git").exists():
            raise CaptureError(f"{path} is not a git clone")
        out.append(path)
    return out


def check(source: dict, http) -> str:
    return "git-log needs no credentials"


def capture(ctx: Context, http=None) -> dict:
    start, end = ctx.fy
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    files, counts = [], {"repos": 0, "commits": 0}
    for clone in _clones(ctx):
        # Whole history: git filters on committer date in the machine's time zone, while the time basis uses
        # author date in the company's; normalize() applies the fiscal-year window.
        out = subprocess.run(
            ["git", "-C", str(clone), "log", "--all", "--no-merges", f"--pretty=format:{FORMAT}", "--name-only"],
            capture_output=True, text=True, check=True).stdout
        path = ctx.raw_dir / f"{clone.name}.log"
        path.write_text(out, encoding="utf-8")
        files.append(path)
        counts["repos"] += 1
        counts["commits"] += out.count("\x1e")
    manifest.record(ctx.claim_dir, ctx.name, method="git-log", files=files, counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    rows, seen = [], set()
    for path in sorted(ctx.raw_dir.glob("*.log")):
        rel, repo = ctx.rel(path), path.stem
        for record in path.read_text(encoding="utf-8").split("\x1e"):
            if not record.strip():
                continue
            sha, name, email, when, subject, body, files = (record.split("\x1f") + [""] * 7)[:7]
            sha = sha.strip()
            if not sha or sha in seen:
                continue
            ts = parse_iso(when.strip())
            if not activity.in_window(ts, start, end, ctx.tz):
                continue
            seen.add(sha)
            message = f"{subject}\n\n{body}".strip()
            rows.append(activity.make_row(
                source=ctx.name, key=sha, kind="commit", person=ctx.resolver.resolve("git", name, email=email, name=name),
                actor_raw=name, ts=ts, container=repo, paths=[line.strip() for line in files.splitlines() if line.strip()],
                title=subject, excerpt=message, refs=activity.extract_refs(message, list(ctx.regexes)), raw_path=rel, tz=ctx.tz))
    return rows
