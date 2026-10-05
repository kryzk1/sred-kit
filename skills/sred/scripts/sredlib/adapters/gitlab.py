"""GitLab capture through REST v4 (token in GITLAB_TOKEN or the env var named by token_env)."""
from __future__ import annotations

import json
import os
import urllib.parse

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context, capture_window


def _base(source: dict) -> str:
    return source.get("base_url", "https://gitlab.com").rstrip("/") + "/api/v4"


def _headers(source: dict) -> dict:
    env = source.get("token_env", "GITLAB_TOKEN")
    if not os.environ.get(env):
        raise CaptureError(f"set {env} to a GitLab personal access token with read_api scope")
    return {"PRIVATE-TOKEN": os.environ[env]}


def _paged(http, url, headers) -> list:
    out, page = [], "1"
    while page:
        sep = "&" if "?" in url else "?"
        data, hdrs = http.get(f"{url}{sep}page={page}", headers)
        out.extend(data or [])
        page = hdrs.get("x-next-page", "")
    return out


def check(source: dict, http) -> str:
    data, _ = http.get(f"{_base(source)}/user", _headers(source))
    return f"authenticated as {data.get('username')}"


def capture(ctx: Context, http) -> dict:
    h, base = _headers(ctx.source), _base(ctx.source)
    if not ctx.source.get("projects"):
        raise CaptureError('gitlab source needs projects = ["group/project", ...]')
    start, end = capture_window(ctx.fy)
    since, until = f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T23:59:59Z"
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    counts, files = {"projects": 0, "merge_requests": 0, "commits": 0}, []
    for proj in ctx.source["projects"]:
        p = f"{base}/projects/{urllib.parse.quote(proj, safe='')}"
        mrs = _paged(http, f"{p}/merge_requests?state=all&updated_after={since}&created_before={until}&per_page=100", h)
        for mr in mrs:
            iid = mr["iid"]
            mr["_notes"] = _paged(http, f"{p}/merge_requests/{iid}/notes?per_page=100", h)
            mr["_commits"] = _paged(http, f"{p}/merge_requests/{iid}/commits?per_page=100", h)
            mr["_files"] = [d.get("new_path", "") for d in _paged(http, f"{p}/merge_requests/{iid}/diffs?per_page=100", h)]
        commits = _paged(http, f"{p}/repository/commits?since={since}&until={until}&all=true&per_page=100", h)
        path = ctx.raw_dir / f"{proj.replace('/', '__')}.json"
        path.write_text(json.dumps({"project": proj, "merge_requests": mrs, "commits": commits}, indent=1, sort_keys=True), encoding="utf-8")
        files.append(path)
        counts["projects"] += 1
        counts["merge_requests"] += len(mrs)
        counts["commits"] += len(commits)
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=files, counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    rows, seen = [], set()
    regexes = list(ctx.regexes)

    def emit(kind, key, actor, ts, *, email="", name="", **kw):
        when = parse_iso(ts)
        if not activity.in_window(when, start, end, ctx.tz) or key in seen:
            return
        seen.add(key)
        rows.append(activity.make_row(source=ctx.name, key=key, kind=kind, person=ctx.resolver.resolve("gitlab", actor, email=email, name=name),
                                      actor_raw=actor or email, ts=when, tz=ctx.tz, **kw))

    def emit_commit(cm, proj, rel, tags, paths):
        message = cm.get("message") or cm.get("title", "")
        emit("commit", cm["id"], cm.get("author_name", ""), cm.get("authored_date") or cm["created_at"],
             email=cm.get("author_email", ""), name=cm.get("author_name", ""), container=proj, tags=tags, paths=paths,
             title=message, excerpt=message, refs=activity.extract_refs(message, regexes), url=cm.get("web_url", ""), raw_path=rel)

    for path in sorted(ctx.raw_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        proj, rel = data["project"], ctx.rel(path)
        for mr in data["merge_requests"]:
            key = f"{proj}!{mr['iid']}"
            author = (mr.get("author") or {}).get("username", "")
            branch = mr.get("source_branch", "")
            tags = list(mr.get("labels", [])) + ([f"branch:{branch}"] if branch else [])
            paths, desc = mr.get("_files", []), mr.get("description") or ""
            refs = activity.extract_refs(f"{mr.get('title', '')}\n{desc}\n{branch}", regexes, own_key=key)
            common = dict(container=proj, title=mr.get("title", ""), url=mr.get("web_url", ""), raw_path=rel, tags=tags, paths=paths, refs=refs)
            emit("pr_opened", key, author, mr["created_at"], excerpt=desc, **common)
            if mr.get("merged_at"):
                emit("pr_merged", f"{key}:merged", author, mr["merged_at"], **common)
            for note in mr.get("_notes", []):
                if not note.get("system"):
                    emit("pr_comment", f"{key}:note:{note['id']}", (note.get("author") or {}).get("username", ""), note["created_at"],
                         excerpt=note.get("body") or "", **common)
            for cm in mr.get("_commits", []):
                emit_commit(cm, proj, rel, tags + [f"pr:{key}"], paths)
        for cm in data["commits"]:
            emit_commit(cm, proj, rel, [], [])
    return rows
