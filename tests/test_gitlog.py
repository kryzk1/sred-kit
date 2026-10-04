import os
import subprocess
from datetime import date

from sredlib.adapters import Context, get_adapter
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))


def git(repo, *args, when=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Alice Chen", GIT_AUTHOR_EMAIL="alice@acme.test",
               GIT_COMMITTER_NAME="Alice Chen", GIT_COMMITTER_EMAIL="alice@acme.test")
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    # -c flags keep the user's global signing and hook settings out of the test repo
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
                   check=True, capture_output=True, env=env)


def commit(repo, name, msg, when):
    p = repo / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(msg)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", msg, when=when)


def test_git_log_includes_abandoned_branches(tmp_path):
    repo = tmp_path / "clones/vision"
    repo.mkdir(parents=True)
    git(repo, "init", "-q")
    commit(repo, "a.py", "Before FY", "2026-06-01T10:00:00+00:00")
    commit(repo, "planner/b.py", "Test occlusion sampler\n\nRefs ACME-12", "2026-09-02T10:00:00+00:00")
    git(repo, "checkout", "-q", "-b", "exp/abandoned")
    commit(repo, "c.py", "Abandoned idea", "2026-10-01T10:00:00+00:00")
    git(repo, "checkout", "-q", "-")
    resolver = Resolver([{"id": "alice", "name": "Alice Chen", "aliases": "email:alice@acme.test"}])
    ctx = Context(tmp_path, {"name": "git", "kind": "code", "method": "git-log", "paths": ["clones/vision"]}, FY, resolver, (r"[A-Z]+-\d+",))
    assert get_adapter("git-log").capture(ctx) == {"repos": 1, "commits": 3}  # whole history; normalize filters
    rows = sorted(get_adapter("git-log").normalize(ctx), key=lambda r: r["date"])
    assert [r["title"] for r in rows] == ["Test occlusion sampler", "Abandoned idea"]
    assert rows[0]["paths"] == "planner/b.py" and rows[0]["refs"] == "ACME-12" and rows[0]["person"] == "alice"
    assert all(len(r["key"]) == 40 for r in rows) and rows[0]["container"] == "vision"
