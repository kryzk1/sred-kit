import json
from datetime import date

import capture
from sredlib.adapters import Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
API = "https://api.github.com/repos/acme/vision"
SHA1, SHA2 = "a" * 40, "b" * 40
PR = {"number": 7, "title": "Occlusion-aware grasp sampling", "body": "Tests ACME-12 hypothesis", "user": {"login": "achen"},
      "created_at": "2026-09-02T10:00:00Z", "updated_at": "2026-09-05T10:00:00Z", "merged_at": "2026-09-05T10:00:00Z",
      "html_url": "https://github.com/acme/vision/pull/7", "head": {"ref": "exp/occlusion"}, "labels": [{"name": "research"}]}
OLD_PR = dict(PR, number=1, created_at="2026-05-01T10:00:00Z", updated_at="2026-05-02T10:00:00Z", merged_at=None)
RESOLVER = Resolver([
    {"id": "alice", "name": "Alice Chen", "aliases": "github:achen;email:alice@acme.test"},
    {"id": "bob", "name": "Bob Roy", "aliases": "github:broy;email:bob@acme.test"},
])


def routes():
    return [
        ("GET", f"{API}/pulls?state=all", [PR, OLD_PR], {}),
        ("GET", f"{API}/pulls/7/reviews", [{"id": 91, "user": {"login": "broy"}, "state": "CHANGES_REQUESTED", "body": "Try depth prior", "submitted_at": "2026-09-03T10:00:00Z"}], {}),
        ("GET", f"{API}/pulls/7/comments", [], {}),
        ("GET", f"{API}/issues/7/comments", [{"id": 55, "user": {"login": "dependabot[bot]"}, "body": "bump", "created_at": "2026-09-03T11:00:00Z"}], {}),
        ("GET", f"{API}/pulls/7/commits", [{"sha": SHA1, "author": {"login": "achen"}, "html_url": "u1",
                                           "commit": {"message": "Sample grasps by visibility\n\nACME-12", "author": {"date": "2026-09-02T09:00:00Z", "email": "alice@acme.test"}}}], {}),
        ("GET", f"{API}/pulls/7/files", [{"filename": "planner/occlusion.py"}], {}),
        ("GET", f"{API}/commits?since=", [
            {"sha": SHA1, "author": None, "commit": {"message": "dup", "author": {"date": "2026-09-02T09:00:00Z", "email": "alice@acme.test"}}},
            {"sha": SHA2, "author": None, "commit": {"message": "Direct commit", "author": {"date": "2026-10-01T09:00:00Z", "email": "bob@acme.test"}}},
        ], {}),
    ]


def ctx_for(tmp_path):
    src = {"name": "gh", "kind": "code", "tool": "github", "method": "api", "org": "acme", "repos": ["vision"]}
    return Context(tmp_path, src, FY, RESOLVER, (r"[A-Z]+-\d+",))


def test_capture_then_normalize(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    ctx = ctx_for(tmp_path)
    counts = get_adapter("github").capture(ctx, fake_http(routes()))
    assert counts == {"repos": 1, "pulls": 1, "commits": 2}
    assert (tmp_path / "evidence/raw/gh/acme__vision.json").exists()
    assert "gh" in json.loads((tmp_path / "evidence/raw/MANIFEST.json").read_text())["sources"]
    rows = {r["key"]: r for r in get_adapter("github").normalize(ctx)}
    assert set(rows) == {"acme/vision#7", "acme/vision#7:merged", "acme/vision#7:review:91", "acme/vision#7:comment:55", SHA1, SHA2}
    opened = rows["acme/vision#7"]
    assert opened["person"] == "alice" and opened["tags"] == "research;branch:exp/occlusion"
    assert opened["paths"] == "planner/occlusion.py" and opened["refs"] == "ACME-12"
    assert rows["acme/vision#7:review:91"]["person"] == "bob"
    assert rows["acme/vision#7:comment:55"]["person"] == "bot"
    assert rows[SHA1]["tags"] == "research;branch:exp/occlusion;pr:acme/vision#7"
    assert rows[SHA2]["person"] == "bob"


def test_pagination_follows_link_header(tmp_path, fake_http, monkeypatch):
    from sredlib.adapters import github

    url1 = "https://api.github.com/orgs/acme/repos?per_page=100&type=all"
    url2 = url1 + "&page=2"
    http = fake_http([
        ("GET", url2, [{"full_name": "acme/b"}], {}),
        ("GET", url1, [{"full_name": "acme/a"}], {"Link": f'<{url2}>; rel="next"'}),
    ])
    assert github._repos({"org": "acme"}, http, {}) == ["acme/a", "acme/b"]


def test_check_source_variants(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    http = fake_http([("GET", "https://api.github.com/user", {"login": "achen"}, {})])
    assert capture.check_source(tmp_path, {"name": "gh", "method": "api", "tool": "github"}, http) == (True, "authenticated as achen")
    ok, msg = capture.check_source(tmp_path, {"name": "j", "method": "export", "export_path": "exports/j.csv"}, http)
    assert not ok and "missing" in msg
    ok, msg = capture.check_source(tmp_path, {"name": "g", "method": "git-log", "paths": ["nope"]}, http)
    assert not ok and "nope" in msg
    assert capture.check_source(tmp_path, {"name": "n", "method": "connector"}, http)[0]
