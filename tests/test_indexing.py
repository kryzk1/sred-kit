from datetime import datetime, timezone

import pytest

import index
from sredlib import activity, config, indexing

TOML = """
[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
export_path = "exports/jira.csv"
mapping = "jira-csv"
issue_key_regex = '[A-Z]+-\\d+'

[[sources]]
name = "notes"
kind = "docs"
tool = "notion"
method = "connector"
"""


def test_build_merges_sources_and_reports_unmatched(make_claim, fixtures):
    claim = make_claim(TOML, roster=[{"id": "alice", "name": "Alice Chen", "classification": "employee", "aliases": "jira:alice chen"}])
    (claim / "exports").mkdir()
    (claim / "exports/jira.csv").write_bytes((fixtures / "exports/jira.csv").read_bytes())
    page = claim / "evidence/raw/notes/page1.json"
    page.parent.mkdir(parents=True)
    page.write_text("{}")
    activity.write_rows(claim / "evidence/raw/notes/rows.csv", [activity.make_row(
        source="notes", key="page1:edit", kind="doc_edit", person="", actor_raw="Alice Chen",
        ts=datetime(2026, 9, 9, tzinfo=timezone.utc), title="Grasp experiment log", raw_path="evidence/raw/notes/page1.json", weight="summary")])
    cfg = config.load_config(claim / "sred.toml")
    summary = indexing.build(cfg, claim)
    assert summary["sources"] == {"jira": 4, "notes": 1} and summary["rows"] == 5 and summary["unmatched"] == 2
    header, rows = activity.read_rows(claim / "evidence/index/activity.csv")
    assert header == activity.COLUMNS and len(rows) == 5
    assert next(r for r in rows if r["source"] == "notes")["person"] == "alice"
    unmatched = (claim / "evidence/index/identities_unmatched.csv").read_text().splitlines()
    assert unmatched[0] == ",".join(indexing.UNMATCHED_COLUMNS)
    assert any(line.startswith("jira,Bob Roy,1,") for line in unmatched)
    assert any(line.startswith("jira,5b10ac,1,") for line in unmatched)
    assert indexing.validate(cfg, claim) == []


def test_build_names_uncaptured_api_source(make_claim):
    claim = make_claim('[[sources]]\nname = "gh"\nkind = "code"\ntool = "github"\nmethod = "api"\norg = "acme"\n', roster=[])
    with pytest.raises(FileNotFoundError, match=r"'gh'.*capture.py github --source gh"):
        indexing.build(config.load_config(claim / "sred.toml"), claim)


def test_cli_build_and_validate(make_claim, capsys):
    claim = make_claim('[[sources]]\nname = "gh"\nkind = "code"\ntool = "github"\nmethod = "api"\norg = "acme"\n', roster=[])
    assert index.main(["build", "--claim", str(claim)]) == 2
    assert "capture.py github" in capsys.readouterr().err
    assert index.main(["validate", "--claim", str(claim)]) == 1
    assert "run index.py build" in capsys.readouterr().out


def test_rows_without_an_actor_are_not_counted_as_unmatched_people(make_claim):
    claim = make_claim('[[sources]]\nname = "notes"\nkind = "docs"\ntool = "notion"\nmethod = "connector"\n', roster=[])
    page = claim / "evidence/raw/notes/p.json"
    page.parent.mkdir(parents=True)
    page.write_text("{}")
    activity.write_rows(claim / "evidence/raw/notes/rows.csv", [activity.make_row(
        source="notes", key="p:1", kind="doc_edit", person="unmatched:", actor_raw="", ts=datetime(2026, 9, 9, tzinfo=timezone.utc),
        raw_path="evidence/raw/notes/p.json")])
    summary = indexing.build(config.load_config(claim / "sred.toml"), claim)
    assert (summary["unmatched"], summary["no_actor"]) == (0, 1)
