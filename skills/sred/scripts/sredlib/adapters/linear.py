"""Linear capture through the GraphQL API (LINEAR_API_KEY or the env var named by token_env)."""
from __future__ import annotations

import json
import os

from .. import activity, manifest
from ..dates import parse_iso
from . import CaptureError, Context, capture_window

URL = "https://api.linear.app/graphql"
USER = "{ id name email }"
QUERY = """query($after: String, $filter: IssueFilter) {
  issues(first: 10, after: $after, includeArchived: true, filter: $filter) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id identifier title description url branchName
      createdAt startedAt completedAt canceledAt archivedAt updatedAt
      state { name type } team { key } project { name } labels { nodes { name } }
      assignee USER creator USER
      attachments { nodes { url } }
      history(first: 50) { pageInfo { hasNextPage } nodes { id createdAt actor USER fromState { name } toState { name } toAssignee USER } }
      comments(first: 50) { pageInfo { hasNextPage } nodes { id createdAt body user USER } }
    }
  }
}""".replace("USER", USER)


def _headers(source: dict) -> dict:
    env = source.get("token_env", "LINEAR_API_KEY")
    if not os.environ.get(env):
        raise CaptureError(f"set {env} to a Linear personal API key")
    return {"Authorization": os.environ[env]}


def _gql(http, source: dict, query: str, variables: dict) -> dict:
    data, _ = http.post(URL, {"query": query, "variables": variables}, _headers(source))
    if data.get("errors"):
        raise CaptureError(f"Linear API error: {data['errors'][0].get('message')}")
    return data["data"]


def check(source: dict, http) -> str:
    return f"authenticated as {_gql(http, source, 'query { viewer { name } }', {})['viewer']['name']}"


def capture(ctx: Context, http) -> dict:
    start, end = capture_window(ctx.fy)
    flt = {"updatedAt": {"gte": f"{start.isoformat()}T00:00:00.000Z"}, "createdAt": {"lte": f"{end.isoformat()}T23:59:59.999Z"}}
    issues, after, truncated = [], None, []
    while True:
        page = _gql(http, ctx.source, QUERY, {"after": after, "filter": flt})["issues"]
        for node in page["nodes"]:
            issues.append(node)
            for part in ("history", "comments"):
                if node[part]["pageInfo"]["hasNextPage"]:
                    truncated.append(f"{node['identifier']} {part} capped at 50")
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    ctx.raw_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.raw_dir / "issues.json"
    path.write_text(json.dumps({"issues": issues}, indent=1, sort_keys=True), encoding="utf-8")
    counts = {"issues": len(issues), "comments": sum(len(i["comments"]["nodes"]) for i in issues),
              "history": sum(len(i["history"]["nodes"]) for i in issues)}
    manifest.record(ctx.claim_dir, ctx.name, method="api", files=[path], counts=counts,
                    date_range=(start.isoformat(), end.isoformat()), notes=truncated)
    return counts


def normalize(ctx: Context) -> list[dict]:
    start, end = ctx.fy
    path = ctx.raw_dir / "issues.json"
    rel, rows = ctx.rel(path), []
    for issue in json.loads(path.read_text(encoding="utf-8"))["issues"]:
        ident = issue["identifier"]
        container = (issue.get("project") or {}).get("name") or (issue.get("team") or {}).get("key", "")
        branch = issue.get("branchName") or ""
        tags = [label["name"] for label in issue["labels"]["nodes"]] + [f"state:{issue['state']['name']}"] + ([f"branch:{branch}"] if branch else [])
        text = "\n".join([issue.get("title", ""), issue.get("description") or ""] + [a["url"] for a in issue["attachments"]["nodes"]])
        refs = activity.extract_refs(text, list(ctx.regexes), own_key=ident)
        events = [("issue_created", ident, issue.get("creator"), issue["createdAt"], issue.get("description") or "", [])]
        for h in issue["history"]["nodes"]:
            if h.get("toState"):
                events.append(("issue_state_change", f"{ident}:state:{h['id']}", h.get("actor"), h["createdAt"], "", [f"to:{h['toState']['name']}"]))
            if h.get("toAssignee"):
                events.append(("issue_assigned", f"{ident}:assign:{h['id']}", h["toAssignee"], h["createdAt"], "", []))
        for c in issue["comments"]["nodes"]:
            events.append(("issue_comment", f"{ident}:comment:{c['id']}", c.get("user"), c["createdAt"], c.get("body") or "", []))
        if issue.get("completedAt"):
            events.append(("issue_resolved", f"{ident}:resolved", issue.get("assignee"), issue["completedAt"], "", []))
        for kind, key, user, ts, excerpt, extra in events:
            if not user:
                continue
            when = parse_iso(ts)
            if not activity.in_window(when, start, end, ctx.tz):
                continue
            person = ctx.resolver.resolve("linear", user.get("id", ""), email=user.get("email", ""), name=user.get("name", ""))
            rows.append(activity.make_row(source=ctx.name, key=key, kind=kind, person=person, actor_raw=user.get("name", "") or user.get("email", ""),
                                          ts=when, container=container, tags=tags + extra, title=issue.get("title", ""), excerpt=excerpt,
                                          refs=refs, url=issue.get("url", ""), raw_path=rel, tz=ctx.tz))
    return rows
