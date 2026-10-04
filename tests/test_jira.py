from datetime import date

import pytest

from sredlib.adapters import CaptureError, Context, get_adapter
from sredlib.adapters.jira import adf_text
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
BASE = "https://acme.atlassian.net"
BOB = {"accountId": "5b10ac", "displayName": "Bob Roy"}
ALICE = {"accountId": "a1", "displayName": "Alice Chen", "emailAddress": "alice@acme.test"}


def doc(text):
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


C100 = {"id": "100", "author": BOB, "created": "2026-09-05T11:00:00.000+0000", "body": doc("Failed at 40% occlusion")}
C101 = {"id": "101", "author": ALICE, "created": "2026-09-06T14:00:00.000+0000", "body": doc("Retry with depth prior")}
ISSUE = {"key": "ACME-12", "fields": {
    "summary": "Grasp planner under occlusion", "issuetype": {"name": "Story"}, "status": {"name": "Done"}, "project": {"key": "ACME"},
    "assignee": BOB, "reporter": ALICE, "creator": ALICE, "created": "2026-09-03T09:05:00.000+0000",
    "resolutiondate": "2026-09-20T16:30:00.000+0000", "labels": ["research"], "description": doc("Beats ACME-7 baseline?"),
    "comment": {"total": 2, "comments": [C100]}},
    "changelog": {"total": 1, "histories": [{"id": "900", "author": BOB, "created": "2026-09-04T10:00:00.000+0000",
                                             "items": [{"field": "status", "toString": "In Progress"}, {"field": "assignee", "to": "5b10ac", "toString": "Bob Roy"}]}]}}


def search(body):
    if "nextPageToken" not in body:
        return {"issues": [ISSUE], "nextPageToken": "t2", "isLast": False}
    return {"issues": [], "isLast": True}


def test_adf_text_flattens_paragraphs():
    assert adf_text(doc("a")) == "a\n" and adf_text(None) == ""


def test_capture_fetches_missing_comments_and_normalizes(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("JIRA_EMAIL", "me@acme.test")
    monkeypatch.setenv("JIRA_TOKEN", "t")
    resolver = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "jira:a1"}, {"id": "bob", "name": "Bob Roy", "aliases": "jira:5b10ac"}])
    ctx = Context(tmp_path, {"name": "jira", "kind": "tracker", "tool": "jira", "method": "api", "base_url": BASE, "projects": ["ACME"]}, FY, resolver, (r"[A-Z]+-\d+",))
    http = fake_http([
        ("POST", f"{BASE}/rest/api/3/search/jql", search, {}),
        ("GET", f"{BASE}/rest/api/3/issue/ACME-12/comment?startAt=0", {"total": 2, "comments": [C100, C101]}, {}),
    ])
    assert get_adapter("jira").capture(ctx, http) == {"issues": 1}
    assert http.calls[0][2]["jql"].startswith("project in (ACME) AND updated >= \"2026-08-01\"")
    rows = {r["key"]: r for r in get_adapter("jira").normalize(ctx)}
    assert set(rows) == {"ACME-12", "ACME-12:history:900:status", "ACME-12:history:900:assignee", "ACME-12:comment:100", "ACME-12:comment:101", "ACME-12:resolved"}
    assert rows["ACME-12"]["person"] == "alice" and rows["ACME-12"]["refs"] == "ACME-7"
    assert rows["ACME-12"]["url"] == f"{BASE}/browse/ACME-12"
    assert rows["ACME-12:comment:101"]["person"] == "alice" and rows["ACME-12:resolved"]["person"] == "bob"


def test_missing_credentials(tmp_path, fake_http, monkeypatch):
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    ctx = Context(tmp_path, {"name": "jira", "tool": "jira", "method": "api", "base_url": BASE}, FY, Resolver([]))
    with pytest.raises(CaptureError, match="JIRA_EMAIL"):
        get_adapter("jira").capture(ctx, fake_http([]))
