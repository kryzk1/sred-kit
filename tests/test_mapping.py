from datetime import date

import pytest

import index
from sredlib import config
from sredlib.mapping import MappingError, import_export, load_mapping
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
ROSTER = [
    {"id": "alice", "name": "Alice Chen", "aliases": "jira:alice chen;email:alice@acme.test;trello:achen"},
    {"id": "bob", "name": "Bob Roy", "aliases": "jira:5b10ac;email:bob@acme.test"},
]


def stage(tmp_path, fixtures, name):
    target = tmp_path / "evidence/raw/src" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((fixtures / "exports" / name).read_bytes())
    return target


def run(mapping, path, tmp_path, regexes=(r"[A-Z]+-\d+",)):
    return import_export(mapping, path, source="src", resolver=Resolver(ROSTER), regexes=list(regexes), claim_dir=tmp_path, fy=FY)


def test_jira_preset_yields_created_resolved_and_each_comment(tmp_path, fixtures):
    res = run(load_mapping("jira-csv", tmp_path), stage(tmp_path, fixtures, "jira.csv"), tmp_path)
    by_key = {r["key"]: r for r in res.rows}
    assert set(by_key) == {"ACME-12", "ACME-12:issue_resolved", "ACME-12:issue_comment:1", "ACME-12:issue_comment:2"}
    created = by_key["ACME-12"]
    assert created["kind"] == "issue_created" and created["person"] == "alice"
    assert created["timestamp"] == "2026-09-03T09:05:00Z"
    assert created["tags"] == "Story;Done;research;vision"
    assert created["refs"] == "ACME-7"
    assert by_key["ACME-12:issue_comment:1"]["person"] == "bob"
    assert by_key["ACME-12:issue_comment:2"]["excerpt"] == "Retrying with depth prior"
    assert res.skipped_outside_fy == 2
    assert res.warnings and "not been verified" in res.warnings[0]


def test_linear_preset_parses_js_dates_and_email_actor(tmp_path, fixtures):
    res = run(load_mapping("linear-csv", tmp_path), stage(tmp_path, fixtures, "linear.csv"), tmp_path)
    created = next(r for r in res.rows if r["key"] == "ACME-40")
    assert created["person"] == "alice" and created["date"] == "2026-10-02"
    assert created["container"] == "Perception"
    assert {r["kind"] for r in res.rows} == {"issue_created", "issue_state_change", "issue_resolved"}
    assert not res.warnings


def test_missing_required_column_is_fatal(tmp_path):
    path = tmp_path / "evidence/raw/src/bad.csv"
    path.parent.mkdir(parents=True)
    path.write_text("Summary,Created\nx,03/Sep/26 9:05 AM\n")
    with pytest.raises(MappingError, match="Issue key"):
        run(load_mapping("jira-csv", tmp_path), path, tmp_path)


def test_bad_date_is_reported_not_fatal(tmp_path):
    path = tmp_path / "evidence/raw/src/d.csv"
    path.parent.mkdir(parents=True)
    path.write_text("Issue key,Summary,Created,Resolved,Reporter\nACME-1,x,yesterday,,Alice Chen\n")
    res = run(load_mapping("jira-csv", tmp_path), path, tmp_path)
    assert res.rows == [] and "yesterday" in res.failures[0]
    assert "Assignee" in res.missing_columns


def test_excel_bom_header_is_tolerated(tmp_path):
    path = tmp_path / "evidence/raw/src/bom.csv"
    path.parent.mkdir(parents=True)
    path.write_bytes("﻿Issue key,Summary,Created,Resolved,Reporter\nACME-5,x,03/Sep/26 9:05 AM,,Alice Chen\n".encode("utf-8"))
    res = run(load_mapping("jira-csv", tmp_path), path, tmp_path)
    assert [r["key"] for r in res.rows] == ["ACME-5"]


def test_custom_json_mapping_for_tool_without_preset(tmp_path, fixtures):
    path = stage(tmp_path, fixtures, "trello.json")
    (tmp_path / "trello-mapping.toml").write_text((fixtures / "exports" / "trello-mapping.toml").read_text())
    res = run(load_mapping("trello-mapping.toml", tmp_path), path, tmp_path)
    assert sorted((r["kind"], r["person"]) for r in res.rows) == [("issue_comment", "alice"), ("issue_created", "alice")]
    assert {r["container"] for r in res.rows} == {"Grasping"}


def test_unknown_preset_lists_available(tmp_path):
    with pytest.raises(MappingError, match="jira-csv"):
        load_mapping("nope", tmp_path)


def test_index_import_cli_stages_raw_copy_and_writes_part(make_claim, fixtures, capsys):
    claim = make_claim("""
[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
export_path = "exports/jira.csv"
mapping = "jira-csv"
issue_key_regex = '[A-Z]+-\\d+'
""", roster=[{"id": "alice", "name": "Alice Chen", "classification": "employee", "aliases": "jira:alice chen"}])
    (claim / "exports").mkdir()
    (claim / "exports/jira.csv").write_bytes((fixtures / "exports/jira.csv").read_bytes())
    assert index.main(["import", "--claim", str(claim), "--source", "jira"]) == 0
    out = capsys.readouterr().out
    assert "jira: 4 rows, 2 outside the fiscal year" in out
    assert "Unmatched people" in out and "Bob Roy" in out
    assert (claim / "evidence/raw/jira/jira.csv").exists()
    assert (claim / "evidence/index/parts/jira.csv").exists()
    assert "jira" in (claim / "evidence/raw/MANIFEST.json").read_text()


def test_index_import_cli_reports_fatal_error(make_claim, capsys):
    claim = make_claim('[[sources]]\nname = "x"\nkind = "tracker"\ntool = "jira"\nmethod = "export"\nexport_path = "missing.csv"\nmapping = "jira-csv"\n')
    assert index.main(["import", "--claim", str(claim), "--source", "x"]) == 2
    assert "export file not found" in capsys.readouterr().err
