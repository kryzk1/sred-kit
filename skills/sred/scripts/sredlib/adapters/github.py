"""GitHub capture through the REST API (token from GITHUB_TOKEN or `gh auth token`)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse

from .. import activity, manifest
from ..dates import parse_iso
from ..http import HttpError
from . import CaptureError, Context, capture_window

API = "https://api.github.com"
_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')
SQUASH_RE = re.compile(r"\(#(\d+)\)\s*$")


def _token(source: dict) -> str:
    env = source.get("token_env", "GITHUB_TOKEN")
    if os.environ.get(env):
        return os.environ[env]
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CaptureError(f"no GitHub token: set {env} or run `gh auth login`") from exc
    if not out:
        raise CaptureError(f"no GitHub token: set {env} or run `gh auth login`")
    return out


def _headers(source: dict) -> dict:
    return {"Authorization": f"Bearer {_token(source)}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _next(headers: dict):
    m = _NEXT_RE.search(headers.get("link", ""))
    return m.group(1) if m else None


def _paged(http, url, headers) -> list:
    out = []
    while url:
        data, hdrs = http.get(url, headers)
        out.extend(data or [])
        url = _next(hdrs)
    return out


def _repos(source: dict, http, headers) -> list[str]:
    if source.get("repos"):
        return [r if "/" in r else f"{source['org']}/{r}" for r in source["repos"]]
    if not source.get("org"):
        raise CaptureError("github source needs org or repos")
    return sorted(r["full_name"] for r in _paged(http, f"{API}/orgs/{source['org']}/repos?per_page=100&type=all", headers))


def _cache_get(path, stamp):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["value"] if data.get("stamp") == stamp else None


def _cache_put(path, stamp, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"stamp": stamp, "value": value}, sort_keys=True), encoding="utf-8")


def check(source: dict, http) -> str:
    data, _ = http.get(f"{API}/user", _headers(source))
    return f"authenticated as {data.get('login')}"


def capture(ctx: Context, http) -> dict:
    h = _headers(ctx.source)
    history = ctx.source.get("commit_history", True)
    start, end = capture_window(ctx.fy)
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    counts, files = {"repos": 0, "pulls": 0, "commits": 0}, []
    for full in _repos(ctx.source, http, h):
        base = f"{API}/repos/{full}"
        pulls, url = [], f"{base}/pulls?state=all&sort=updated&direction=desc&per_page=100"
        while url:
            page, hdrs = http.get(url, h)
            stop = False
            for pr in page or []:
                if pr["updated_at"][:10] < start.isoformat():
                    stop = True
                    break
                if pr["created_at"][:10] <= end.isoformat():
                    pulls.append(pr)
            url = None if stop else _next(hdrs)
        # Cache each PR's details and each branch's commits as they arrive, so an interrupted capture of a large
        # repo resumes where it stopped. Entries are reused only while the PR's updated_at or the branch head is unchanged.
        cache = ctx.raw_dir / ".cache" / full.replace("/", "__")
        for pr in pulls:
            n = pr["number"]
            cached = _cache_get(cache / f"pr_{n}.json", pr["updated_at"])
            if cached is None:
                cached = {
                    "_reviews": _paged(http, f"{base}/pulls/{n}/reviews?per_page=100", h),
                    "_review_comments": _paged(http, f"{base}/pulls/{n}/comments?per_page=100", h),
                    "_issue_comments": _paged(http, f"{base}/issues/{n}/comments?per_page=100", h),
                    "_commits": _paged(http, f"{base}/pulls/{n}/commits?per_page=100", h) if history else [],
                    "_files": [f["filename"] for f in _paged(http, f"{base}/pulls/{n}/files?per_page=100", h)],
                }
                _cache_put(cache / f"pr_{n}.json", pr["updated_at"], cached)
            pr.update(cached)
        # Every branch, not just the default: abandoned experiments often never get a PR. With commit_history = false
        # the commit record comes from a git-log source on local clones instead (far cheaper for large repos).
        commits, seen = [], set()
        try:
            branches = _paged(http, f"{base}/branches?per_page=100", h) if history else []
        except HttpError as exc:
            if "HTTP 409" not in str(exc):  # 409 = empty repository
                raise
            branches = []
        window = f"{start.isoformat()}..{end.isoformat()}"
        for b in branches:
            branch, head = b["name"], (b.get("commit") or {}).get("sha")
            key = cache / "branches" / f"{urllib.parse.quote(branch, safe='')}.json"
            listed = _cache_get(key, f"{head}@{window}") if head else None
            if listed is None:
                listed = _paged(http, f"{base}/commits?sha={urllib.parse.quote(branch, safe='')}&since={start.isoformat()}T00:00:00Z"
                                      f"&until={end.isoformat()}T23:59:59Z&per_page=100", h)
                if head:
                    _cache_put(key, f"{head}@{window}", listed)
            for cm in listed:
                if cm["sha"] not in seen:
                    seen.add(cm["sha"])
                    commits.append({**cm, "_branch": branch})
        path = ctx.raw_dir / f"{full.replace('/', '__')}.json"
        path.write_text(json.dumps({"repo": full, "pulls": pulls, "commits": commits}, indent=1, sort_keys=True), encoding="utf-8")
        files.append(path)
        counts["repos"] += 1
        counts["pulls"] += len(pulls)
        counts["commits"] += len(commits)
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=files, counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    rows, seen = [], set()
    regexes = list(ctx.regexes)

    def emit(kind, key, actor, ts, *, email="", **kw):
        when = parse_iso(ts)
        if not activity.in_window(when, start, end, ctx.tz) or key in seen:
            return
        seen.add(key)
        rows.append(activity.make_row(source=ctx.name, key=key, kind=kind, person=ctx.resolver.resolve("github", actor, email=email),
                                      actor_raw=actor or email, ts=when, tz=ctx.tz, **kw))

    def emit_commit(cm, repo, rel, tags, paths):
        info = cm.get("commit") or {}
        author = info.get("author") or {}
        message = info.get("message", "")
        emit("commit", cm["sha"], (cm.get("author") or {}).get("login", ""), author.get("date", ""), email=author.get("email", ""),
             container=repo, tags=tags, paths=paths, title=message, excerpt=message,
             refs=activity.extract_refs(message, regexes), url=cm.get("html_url", ""), raw_path=rel)

    for path in sorted(ctx.raw_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        repo, rel = data["repo"], ctx.rel(path)
        for pr in data["pulls"]:
            key = f"{repo}#{pr['number']}"
            author = (pr.get("user") or {}).get("login", "")
            branch = (pr.get("head") or {}).get("ref", "")
            tags = [label["name"] for label in pr.get("labels", [])] + ([f"branch:{branch}"] if branch else [])
            paths = pr.get("_files", [])
            body = pr.get("body") or ""
            refs = activity.extract_refs(f"{pr.get('title', '')}\n{body}\n{branch}", regexes, own_key=key)
            common = dict(container=repo, title=pr.get("title", ""), url=pr.get("html_url", ""), raw_path=rel, paths=paths, refs=refs)
            emit("pr_opened", key, author, pr["created_at"], tags=tags, excerpt=body, **common)
            if pr.get("merged_at"):
                emit("pr_merged", f"{key}:merged", author, pr["merged_at"], tags=tags, **common)
            for rv in pr.get("_reviews", []):
                if rv.get("submitted_at"):
                    emit("pr_review", f"{key}:review:{rv['id']}", (rv.get("user") or {}).get("login", ""), rv["submitted_at"],
                         tags=tags + [f"state:{rv.get('state', '')}"], excerpt=rv.get("body") or "", **common)
            for c in pr.get("_review_comments", []) + pr.get("_issue_comments", []):
                emit("pr_comment", f"{key}:comment:{c['id']}", (c.get("user") or {}).get("login", ""), c["created_at"],
                     tags=tags, excerpt=c.get("body") or "", **common)
            for cm in pr.get("_commits", []):
                emit_commit(cm, repo, rel, tags + [f"pr:{key}"], paths)
        prs = {pr["number"]: pr for pr in data["pulls"]}
        for cm in data["commits"]:
            tags = [f"branch:{cm['_branch']}"] if cm.get("_branch") else []
            paths: list[str] = []
            m = SQUASH_RE.search(activity.first_line((cm.get("commit") or {}).get("message", "")))
            pr = prs.get(int(m.group(1))) if m else None
            if pr:  # a squash or merge commit carries its PR's labels, branch and files
                tags += [label["name"] for label in pr.get("labels", [])] + [f"pr:{repo}#{pr['number']}"]
                paths = pr.get("_files", [])
            emit_commit(cm, repo, rel, tags, paths)
    return rows
