"""Jira Cloud capture through REST v3 (JIRA_EMAIL + JIRA_TOKEN, or the env names in email_env/token_env)."""
from __future__ import annotations

import base64
import json
import os

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context, capture_window

FIELDS = ["summary", "issuetype", "status", "project", "assignee", "reporter", "creator", "created", "updated",
          "resolutiondate", "labels", "description", "comment"]
BLOCKS = {"paragraph", "heading", "listItem", "codeBlock", "blockquote"}


def _base(source: dict) -> str:
    if not source.get("base_url"):
        raise CaptureError("jira source needs base_url, e.g. https://acme.atlassian.net")
    return source["base_url"].rstrip("/")


def _headers(source: dict) -> dict:
    e_env, t_env = source.get("email_env", "JIRA_EMAIL"), source.get("token_env", "JIRA_TOKEN")
    if not (os.environ.get(e_env) and os.environ.get(t_env)):
        raise CaptureError(f"set {e_env} and {t_env} (an Atlassian API token)")
    cred = base64.b64encode(f"{os.environ[e_env]}:{os.environ[t_env]}".encode()).decode()
    return {"Authorization": f"Basic {cred}"}


def adf_text(node) -> str:
    """Plain text from Atlassian Document Format."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_text(n) for n in node)
    text = node.get("text", "") + adf_text(node.get("content", []))
    return text + ("\n" if node.get("type") in BLOCKS else "")


def check(source: dict, http) -> str:
    data, _ = http.get(f"{_base(source)}/rest/api/3/myself", _headers(source))
    return f"authenticated as {data.get('displayName')}"


def _all(http, url, headers, list_key) -> list:
    out, start_at = [], 0
    while True:
        data, _ = http.get(f"{url}?startAt={start_at}&maxResults=100", headers)
        items = data.get(list_key, [])
        out.extend(items)
        start_at += len(items)
        if not items or start_at >= data.get("total", 0):
            return out


def capture(ctx: Context, http) -> dict:
    base, h = _base(ctx.source), _headers(ctx.source)
    start, end = capture_window(ctx.fy)
    jql = f'updated >= "{start.isoformat()}" AND created <= "{end.isoformat()} 23:59" ORDER BY created ASC'
    if ctx.source.get("projects"):
        jql = f"project in ({', '.join(ctx.source['projects'])}) AND " + jql
    issues, token = [], None
    while True:
        body = {"jql": jql, "fields": FIELDS, "expand": "changelog", "maxResults": 100}
        if token:
            body["nextPageToken"] = token
        data, _ = http.post(f"{base}/rest/api/3/search/jql", body, h)
        issues.extend(data.get("issues", []))
        token = data.get("nextPageToken")
        if data.get("isLast", True) or not token:
            break
    for issue in issues:
        key = issue["key"]
        comment = (issue.get("fields") or {}).get("comment") or {}
        if comment.get("total", 0) > len(comment.get("comments", [])):
            comment["comments"] = _all(http, f"{base}/rest/api/3/issue/{key}/comment", h, "comments")
        log = issue.get("changelog") or {}
        if log.get("total", 0) > len(log.get("histories", [])):
            issue["changelog"] = {"histories": _all(http, f"{base}/rest/api/3/issue/{key}/changelog", h, "values")}
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.raw_dir / "issues.json"
    path.write_text(json.dumps({"base_url": base, "issues": issues}, indent=1, sort_keys=True), encoding="utf-8")
    counts = {"issues": len(issues)}
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=[path], counts=counts, date_range=(start.isoformat(), end.isoformat()))
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    path = ctx.raw_dir / "issues.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    base, rel, rows = data["base_url"], ctx.rel(path), []
    for issue in data["issues"]:
        key, f = issue["key"], issue.get("fields") or {}
        desc = adf_text(f.get("description"))
        tags = [(f.get("issuetype") or {}).get("name", ""), f"state:{(f.get('status') or {}).get('name', '')}"] + list(f.get("labels") or [])
        refs = activity.extract_refs(f"{f.get('summary', '')}\n{desc}", list(ctx.regexes), own_key=key)
        events = [("issue_created", key, f.get("creator") or f.get("reporter"), f.get("created"), desc, [])]
        for hist in (issue.get("changelog") or {}).get("histories", []):
            for item in hist.get("items", []):
                if item.get("field") == "status":
                    events.append(("issue_state_change", f"{key}:history:{hist['id']}:status", hist.get("author"), hist["created"], "",
                                   [f"to:{item.get('toString', '')}"]))
                elif item.get("field") == "assignee" and item.get("to"):
                    events.append(("issue_assigned", f"{key}:history:{hist['id']}:assignee",
                                   {"accountId": item["to"], "displayName": item.get("toString", "")}, hist["created"], "", []))
        for c in (f.get("comment") or {}).get("comments") or []:
            events.append(("issue_comment", f"{key}:comment:{c['id']}", c.get("author"), c["created"], adf_text(c.get("body")), []))
        if f.get("resolutiondate"):
            events.append(("issue_resolved", f"{key}:resolved", f.get("assignee"), f["resolutiondate"], "", []))
        for kind, k, user, ts, excerpt, extra in events:
            if not ts or not user:
                continue
            when = parse_iso(ts)
            if not activity.in_window(when, start, end, ctx.tz):
                continue
            person = ctx.resolver.resolve("jira", user.get("accountId", ""), email=user.get("emailAddress", ""), name=user.get("displayName", ""))
            rows.append(activity.make_row(source=ctx.name, key=k, kind=kind, person=person,
                                          actor_raw=user.get("displayName", "") or user.get("accountId", ""), ts=when,
                                          container=(f.get("project") or {}).get("key", ""), tags=tags + extra, title=f.get("summary", ""),
                                          excerpt=excerpt, refs=refs, url=f"{base}/browse/{key}", raw_path=rel, tz=ctx.tz))
    return rows
