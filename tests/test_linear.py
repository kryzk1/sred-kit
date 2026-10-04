import json
from datetime import date

from sredlib.adapters import Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
ALICE = {"id": "u1", "name": "Alice Chen", "email": "alice@acme.test"}
BOB = {"id": "u2", "name": "Bob Roy", "email": "bob@acme.test"}
ISSUE = {
    "id": "i1", "identifier": "ACME-40", "title": "Compare depth priors", "description": "Follows ACME-12",
    "url": "https://linear.app/acme/issue/ACME-40", "branchName": "achen/acme-40",
    "createdAt": "2026-10-02T17:00:00.000Z", "startedAt": None, "completedAt": "2026-10-12T09:00:00.000Z",
    "canceledAt": None, "archivedAt": None, "updatedAt": "2026-10-12T09:00:00.000Z",
    "state": {"name": "Done", "type": "completed"}, "team": {"key": "ACME"}, "project": {"name": "Perception"},
    "labels": {"nodes": [{"name": "Research"}]}, "assignee": BOB, "creator": ALICE,
    "attachments": {"nodes": [{"url": "https://github.com/acme/vision/pull/7"}]},
    "history": {"pageInfo": {"hasNextPage": False}, "nodes": [
        {"id": "h1", "createdAt": "2026-10-03T09:00:00.000Z", "actor": BOB, "fromState": {"name": "Todo"}, "toState": {"name": "In Progress"}, "toAssignee": None},
        {"id": "h2", "createdAt": "2026-10-02T18:00:00.000Z", "actor": ALICE, "fromState": None, "toState": None, "toAssignee": BOB},
    ]},
    "comments": {"pageInfo": {"hasNextPage": True}, "nodes": [
        {"id": "c1", "createdAt": "2026-10-05T09:00:00.000Z", "body": "Prior B diverged", "user": BOB},
    ]},
}
OLD = dict(ISSUE, id="i0", identifier="ACME-3", createdAt="2026-06-01T00:00:00.000Z", completedAt=None,
           history={"pageInfo": {"hasNextPage": False}, "nodes": []}, comments={"pageInfo": {"hasNextPage": False}, "nodes": []})


def pages(body):
    if body["variables"]["after"] is None:
        return {"data": {"issues": {"pageInfo": {"hasNextPage": True, "endCursor": "cur1"}, "nodes": [ISSUE]}}}
    return {"data": {"issues": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [OLD]}}}


def test_capture_pages_and_normalize_events(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("LINEAR_API_KEY", "k")
    resolver = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "linear:u1"}, {"id": "bob", "name": "Bob Roy", "aliases": "email:bob@acme.test"}])
    ctx = Context(tmp_path, {"name": "lin", "kind": "tracker", "tool": "linear", "method": "api"}, FY, resolver, (r"[A-Z]+-\d+",))
    http = fake_http([("POST", "https://api.linear.app/graphql", pages, {})])
    counts = get_adapter("linear").capture(ctx, http)
    assert counts == {"issues": 2, "comments": 1, "history": 2}
    assert http.calls[0][2]["variables"]["filter"]["updatedAt"]["gte"] == "2026-07-30T00:00:00.000Z"
    notes = json.loads((tmp_path / "evidence/raw/MANIFEST.json").read_text())["sources"]["lin"]["notes"]
    assert notes == ["ACME-40 comments capped at 50"]
    rows = {r["key"]: r for r in get_adapter("linear").normalize(ctx)}
    assert set(rows) == {"ACME-40", "ACME-40:state:h1", "ACME-40:assign:h2", "ACME-40:comment:c1", "ACME-40:resolved"}
    assert rows["ACME-40"]["person"] == "alice" and rows["ACME-40"]["container"] == "Perception"
    assert rows["ACME-40"]["refs"] == "ACME-12;acme/vision#7"
    assert rows["ACME-40:assign:h2"]["person"] == "bob"
    assert rows["ACME-40:state:h1"]["tags"].endswith("to:In Progress")
