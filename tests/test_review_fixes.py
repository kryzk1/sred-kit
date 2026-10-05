"""Regression tests for the whole-branch review findings."""
import csv
import io
import os
import subprocess
import urllib.error
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

import capture
from sredlib import activity, handoff, timebasis
from sredlib.adapters import Context, get_adapter
from sredlib.http import Http
from sredlib.mapping import import_export, load_mapping
from sredlib.roster import ROSTER_COLUMNS, Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
TORONTO = ZoneInfo("America/Toronto")
RESOLVER = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "github:achen;gitlab:achen;email:alice@acme.test"}])


# Finding 1: capture windows must cover the company-local fiscal year

def gh_routes(api, pr, commits_by_branch):
    routes = [("GET", f"{api}/pulls?state=all", [pr], {})]
    for sub in ("reviews", "comments", "commits", "files"):
        routes.append(("GET", f"{api}/pulls/{pr['number']}/{sub}", [], {}))
    routes.append(("GET", f"{api}/issues/{pr['number']}/comments", [], {}))
    routes.append(("GET", f"{api}/branches", [{"name": b} for b in commits_by_branch], {}))
    for branch, commits in commits_by_branch.items():
        routes.append(("GET", f"{api}/commits?sha={branch.replace('/', '%2F')}&", commits, {}))
    return routes


def test_github_capture_keeps_events_on_the_local_last_day(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    api = "https://api.github.com/repos/acme/vision"
    late = "2027-08-01T02:30:00Z"  # 22:30 on July 31 in Toronto
    pr = {"number": 9, "title": "Late PR", "body": "", "user": {"login": "achen"}, "created_at": late, "updated_at": late,
          "merged_at": None, "html_url": "u", "head": {"ref": "exp/late"}, "labels": []}
    commit = {"sha": "d" * 40, "author": {"login": "achen"}, "commit": {"message": "Late commit", "author": {"date": late, "email": "alice@acme.test"}}}
    http = fake_http(gh_routes(api, pr, {"main": [commit]}))
    ctx = Context(tmp_path, {"name": "gh", "kind": "code", "tool": "github", "method": "api", "org": "acme", "repos": ["vision"]}, FY, RESOLVER, (), TORONTO)
    get_adapter("github").capture(ctx, http)
    commit_url = next(url for _, url, _ in http.calls if "/commits?sha=" in url)
    assert "since=2026-07-30" in commit_url and "until=2027-08-02" in commit_url
    rows = {r["key"]: r for r in get_adapter("github").normalize(ctx)}
    assert rows["acme/vision#9"]["date"] == "2027-07-31" and rows["d" * 40]["date"] == "2027-07-31"


def test_gitlab_linear_jira_windows_are_padded(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITLAB_TOKEN", "t")
    monkeypatch.setenv("LINEAR_API_KEY", "k")
    monkeypatch.setenv("JIRA_EMAIL", "e")
    monkeypatch.setenv("JIRA_TOKEN", "t")
    gl = fake_http([("GET", "https://gitlab.com/api/v4/projects/", [], {})])
    get_adapter("gitlab").capture(Context(tmp_path, {"name": "gl", "tool": "gitlab", "method": "api", "projects": ["acme/vision"]}, FY, RESOLVER), gl)
    assert "updated_after=2026-07-30T00:00:00Z" in gl.calls[0][1] and "created_before=2027-08-02T23:59:59Z" in gl.calls[0][1]
    lin = fake_http([("POST", "https://api.linear.app/graphql", {"data": {"issues": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []}}}, {})])
    get_adapter("linear").capture(Context(tmp_path, {"name": "lin", "tool": "linear", "method": "api"}, FY, RESOLVER), lin)
    flt = lin.calls[0][2]["variables"]["filter"]
    assert flt["updatedAt"]["gte"] == "2026-07-30T00:00:00.000Z" and flt["createdAt"]["lte"] == "2027-08-02T23:59:59.999Z"
    jira = fake_http([("POST", "https://acme.atlassian.net/rest/api/3/search/jql", {"issues": [], "isLast": True}, {})])
    get_adapter("jira").capture(Context(tmp_path, {"name": "jira", "tool": "jira", "method": "api", "base_url": "https://acme.atlassian.net"}, FY, RESOLVER), jira)
    jql = jira.calls[0][2]["jql"]
    assert 'updated >= "2026-07-30"' in jql and 'created <= "2027-08-02 23:59"' in jql


def git(repo, *args, when=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Alice Chen", GIT_AUTHOR_EMAIL="alice@acme.test",
               GIT_COMMITTER_NAME="Alice Chen", GIT_COMMITTER_EMAIL="alice@acme.test")
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                   check=True, capture_output=True, env=env)


def test_git_log_keeps_late_local_commit(tmp_path, monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    repo = tmp_path / "clones/vision"
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "a.py").write_text("x")
    git(repo, "add", "a.py")
    git(repo, "commit", "-q", "-m", "Late local commit", when="2027-08-01T08:30:00+00:00")  # 22:30 July 31 in Honolulu
    ctx = Context(tmp_path, {"name": "git", "kind": "code", "method": "git-log", "paths": ["clones/vision"]}, FY, RESOLVER, (), ZoneInfo("Pacific/Honolulu"))
    get_adapter("git-log").capture(ctx)
    assert [r["date"] for r in get_adapter("git-log").normalize(ctx)] == ["2027-07-31"]


# Finding 2: export times without a time zone are company-local

def test_naive_export_times_are_company_local(tmp_path):
    path = tmp_path / "evidence/raw/src/asana.csv"
    path.parent.mkdir(parents=True)
    path.write_text("Task ID,Created At,Completed At,Name,Assignee,Assignee Email,Notes,Projects\n"
                    "1,2026-08-01,,First day task,Alice Chen,alice@acme.test,,Grasping\n")
    res = import_export(load_mapping("asana-csv", tmp_path), path, source="a", resolver=RESOLVER, regexes=[], claim_dir=tmp_path, fy=FY, tz=TORONTO)
    assert [(r["date"], r["timestamp"]) for r in res.rows] == [("2026-08-01", "2026-08-01T04:00:00Z")]
    assert res.skipped_outside_fy == 0


# Finding 4: confirmed percentages must be numbers between 0 and 100

def person(**kw):
    base = {c: "" for c in ROSTER_COLUMNS}
    base.update(kw)
    return base


ALICE = person(id="alice", name="Alice Chen", classification="employee", in_canada="Y", paid_hours="2080", wages_earned="100000.00")
CAROL = person(id="carol", name="Carol Diaz", classification="contractor", in_canada="Y", arms_length="Y", contract_provided="Y",
               sred_in_contract="N", wages_earned="50000.10")
MONTHS = {("alice", "2026-09"): {"evidence_days": 1, "sred_days": 1.0, "by_project": {}}}


@pytest.mark.parametrize("value", ["755", "-5", "TBD", "75 percent"])
def test_bad_confirmed_pct_is_rejected_by_name(value):
    with pytest.raises(timebasis.TimeBasisError, match="alice"):
        timebasis.summarize([ALICE], MONTHS, [], FY, "balanced", [{"person": "alice", "confirmed_pct": value}])


# Finding 8: claimant entries survive Excel reformatting and are never dropped silently

def test_month_keys_are_normalized():
    for raw in ("Oct-26", "2026-10", "10/2026", "Oct 2026", "October 2026", "2026-10-01"):
        assert timebasis.normalize_month(raw) == "2026-10"


def test_unmatched_entries_are_kept_and_reported(make_claim):
    claim = make_claim('[claim]\nscenario = "balanced"\n[payroll]\ntotal_wages_earned = 100000.00\n', roster=[ALICE])
    activity.write_rows(claim / "evidence/index/activity.csv", [activity.make_row(
        source="gh", key="a" * 40, kind="commit", person="alice", actor_raw="achen", ts=datetime.fromisoformat("2026-09-02T12:00:00+00:00"),
        raw_path="evidence/raw/gh/x.json")])
    fin = claim / "financials"
    fin.mkdir()
    (fin / "gap_months.csv").write_text("person,month,basis,basis_source,corroborated,basis_share\n"
                                        "alice,Nov-26,design reviews,calendar,Y,60\n"
                                        "alice,2026-09,stale entry,,,10\n")
    (fin / "person_summary.csv").write_text("person,confirmed_pct,basis\nalice-old,50,renamed id\n")
    timebasis.run(claim)
    gaps = {r["month"]: r for r in csv.DictReader((fin / "gap_months.csv").open())}
    assert gaps["2026-11"]["basis"] == "design reviews"
    assert "stale entry" in (fin / "gap_months_unmatched.csv").read_text()
    assert "alice-old" in (fin / "person_summary_unmatched.csv").read_text()
    checks = (fin / "financial_checks.md").read_text()
    assert "gap_months_unmatched.csv" in checks and "person_summary_unmatched.csv" in checks


# Finding 10 (re-graded): the labour summary carries the arm's-length flag

def test_labour_summary_has_arms_length_column():
    summary = [{"person": "alice", "confirmed_pct": "75", "proposed_pct": "75"}, {"person": "carol", "confirmed_pct": "50", "proposed_pct": "50"}]
    rows = timebasis.labour_summary([ALICE, CAROL], summary, timebasis.load_columns({"_dir": "."}))
    col = rows[0].index("Arm's Length")
    assert rows[2][col] == "Y"


# Finding 5: handoff compares the labour summary with confirmed percentages

def test_handoff_flags_stale_labour_summary_and_bad_pct(make_claim):
    claim = make_claim(roster=[ALICE])
    (claim / "scope").mkdir()
    (claim / "scope/projects.toml").write_text('[[project]]\nid = "P1"\ntitle = "T"\n')
    (claim / "draft/P1").mkdir(parents=True)
    (claim / "draft/P1/narrative.md").write_text("# P1: T\n\n## Section A\n- 200 Project title: T\n\n## Section C\n- Key individuals: Alice Chen (Lead)\n")
    (claim / "financials").mkdir()
    (claim / "financials/person_summary.csv").write_text("person,confirmed_pct\nalice,80\n")
    (claim / "handoff").mkdir()
    for name in ("evidence_index.csv", "decision_log.md", "gaps.md", "README.md", "T661-Part2-P1.md"):
        (claim / "handoff" / name).write_text("x")
    (claim / "handoff/labour_summary.csv").write_text("Name,SRED %\nAlice Chen,75.00%\nTOTAL,75.00%\n")
    assert any("stale" in f.message for f in handoff.check(claim))
    (claim / "financials/person_summary.csv").write_text("person,confirmed_pct\nalice,TBD\n")
    assert any("not a percentage" in f.message for f in handoff.check(claim))


# Finding 6: GitHub's secondary rate limit is retried

class Resp:
    def __init__(self, body, headers=None):
        self.body, self.headers = body, headers or {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_secondary_rate_limit_is_retried(monkeypatch):
    calls, slept = [], []

    def fake_urlopen(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 403, "forbidden", {"X-RateLimit-Remaining": "4000", "Retry-After": "2"},
                                         io.BytesIO(b'{"message": "You have exceeded a secondary rate limit"}'))
        return Resp(b"[]")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert Http(sleep=slept.append).get("https://api.github.com/x")[0] == [] and slept == [2.0]


# Finding 7: smaller Linear pages, and capture prints truncation notes

def test_linear_page_size_and_capture_prints_notes(make_claim, fake_http, monkeypatch, capsys):
    from sredlib.adapters import linear

    assert "issues(first: 10," in linear.QUERY
    monkeypatch.setenv("LINEAR_API_KEY", "k")
    node = {"identifier": "ACME-1", "history": {"pageInfo": {"hasNextPage": False}, "nodes": []},
            "comments": {"pageInfo": {"hasNextPage": True}, "nodes": []}}
    page = {"data": {"issues": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": [node]}}}
    claim = make_claim('[[sources]]\nname = "lin"\nkind = "tracker"\ntool = "linear"\nmethod = "api"\n')
    monkeypatch.setattr(capture, "Http", lambda: fake_http([("POST", "https://api.linear.app/graphql", page, {})]))
    assert capture.main(["linear", "--claim", str(claim), "--source", "lin"]) == 0
    assert "ACME-1 comments capped at 50" in capsys.readouterr().out


# Finding 9: GitHub branches without a PR, and squash commits joined to their PR

def test_github_branch_commits_and_squash_join(tmp_path, fake_http, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    api = "https://api.github.com/repos/acme/vision"
    pr = {"number": 7, "title": "Occlusion sampler", "body": "", "user": {"login": "achen"}, "created_at": "2026-09-02T10:00:00Z",
          "updated_at": "2026-09-05T10:00:00Z", "merged_at": "2026-09-05T10:00:00Z", "html_url": "u", "head": {"ref": "exp/occ"},
          "labels": [{"name": "research"}]}
    squash = {"sha": "e" * 40, "author": {"login": "achen"}, "commit": {"message": "Occlusion sampler (#7)", "author": {"date": "2026-09-05T10:00:00Z", "email": ""}}}
    abandoned = {"sha": "f" * 40, "author": {"login": "achen"}, "commit": {"message": "Try voxel grid", "author": {"date": "2026-10-01T10:00:00Z", "email": ""}}}
    routes = gh_routes(api, pr, {"main": [squash], "exp/voxel": [abandoned]})
    routes.insert(0, ("GET", f"{api}/pulls/7/files", [{"filename": "planner/occlusion.py"}], {}))
    ctx = Context(tmp_path, {"name": "gh", "kind": "code", "tool": "github", "method": "api", "org": "acme", "repos": ["vision"]}, FY, RESOLVER)
    get_adapter("github").capture(ctx, fake_http(routes))
    rows = {r["key"]: r for r in get_adapter("github").normalize(ctx)}
    assert rows["f" * 40]["tags"] == "branch:exp/voxel"
    assert rows["e" * 40]["paths"] == "planner/occlusion.py" and "pr:acme/vision#7" in rows["e" * 40]["tags"]
