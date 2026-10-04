from datetime import date

import pytest

from sredlib.adapters import CaptureError, Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
P = "https://gitlab.com/api/v4/projects/acme%2Fvision"
Q = "state=all&updated_after=2026-07-30T00:00:00Z&created_before=2027-08-02T23:59:59Z&per_page=100"  # padded window
SHA = "c" * 40
MR = {"iid": 3, "title": "Depth prior for grasping", "description": "Closes #12", "author": {"username": "achen"},
      "created_at": "2026-09-04T10:00:00Z", "merged_at": None, "web_url": "https://gitlab.com/acme/vision/-/merge_requests/3",
      "source_branch": "exp/depth", "labels": ["research"]}
MR2 = dict(MR, iid=4, title="Abandoned voxel approach", created_at="2026-10-04T10:00:00Z", source_branch="exp/voxel")


def routes():
    return [
        ("GET", f"{P}/merge_requests?{Q}&page=1", [MR], {"X-Next-Page": "2"}),
        ("GET", f"{P}/merge_requests?{Q}&page=2", [MR2], {"X-Next-Page": ""}),
        ("GET", f"{P}/merge_requests/3/notes", [
            {"id": 1, "system": True, "body": "added 1 commit", "author": {"username": "achen"}, "created_at": "2026-09-04T11:00:00Z"},
            {"id": 2, "system": False, "body": "Depth prior overfits", "author": {"username": "broy"}, "created_at": "2026-09-05T11:00:00Z"},
        ], {}),
        ("GET", f"{P}/merge_requests/3/commits", [{"id": SHA, "title": "Add depth prior", "message": "Add depth prior",
                                                   "author_name": "Alice Chen", "author_email": "alice@acme.test", "authored_date": "2026-09-04T09:00:00Z"}], {}),
        ("GET", f"{P}/merge_requests/3/diffs", [{"new_path": "grasp/depth.py"}], {}),
        ("GET", f"{P}/merge_requests/4/", [], {}),
        ("GET", f"{P}/repository/commits", [], {}),
    ]


def test_capture_follows_pages_and_normalize_skips_system_notes(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "t")
    resolver = Resolver([
        {"id": "alice", "name": "Alice Chen", "aliases": "gitlab:achen;email:alice@acme.test"},
        {"id": "bob", "name": "Bob Roy", "aliases": "gitlab:broy"},
    ])
    ctx = Context(tmp_path, {"name": "gl", "kind": "code", "tool": "gitlab", "method": "api", "projects": ["acme/vision"]}, FY, resolver, (r"#\d+",))
    assert get_adapter("gitlab").capture(ctx, fake_http(routes())) == {"projects": 1, "merge_requests": 2, "commits": 0}
    rows = {r["key"]: r for r in get_adapter("gitlab").normalize(ctx)}
    assert set(rows) == {"acme/vision!3", "acme/vision!3:note:2", SHA, "acme/vision!4"}
    assert rows["acme/vision!3"]["refs"] == "#12" and rows["acme/vision!3"]["paths"] == "grasp/depth.py"
    assert rows["acme/vision!3:note:2"]["person"] == "bob"
    assert rows[SHA]["person"] == "alice" and rows[SHA]["tags"] == "research;branch:exp/depth;pr:acme/vision!3"


def test_missing_token_is_a_clear_error(tmp_path, fake_http, monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    ctx = Context(tmp_path, {"name": "gl", "tool": "gitlab", "method": "api", "projects": ["acme/vision"]}, FY, Resolver([]))
    with pytest.raises(CaptureError, match="GITLAB_TOKEN"):
        get_adapter("gitlab").capture(ctx, fake_http([]))
