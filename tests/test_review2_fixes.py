"""Regression tests for the Plan 2 whole-branch review findings."""
import csv
import shutil
from datetime import datetime
from pathlib import Path

import check
from sredlib import activity, handoff, setupcheck, timebasis
from sredlib.roster import ROSTER_COLUMNS

TEMPLATES = Path(__file__).resolve().parent.parent / "skills" / "sred" / "templates"


def person(**kw):
    base = {c: "" for c in ROSTER_COLUMNS}
    base.update(kw)
    return base


ALICE = person(id="alice", name="Alice Chen", classification="employee", in_canada="Y", specified_employee="N",
               aliases="email:alice@acme.test", paid_hours="2080", wages_earned="100000.00")


# Finding 1: preliminary runs use rules only, as the spec and 03-discover-scope.md say

def test_preliminary_ignores_overrides_and_gap_bases(make_claim):
    claim = make_claim('[claim]\nscenario = "maximum"\n[[classification.rules]]\nid = "r1"\nproject = "P1"\nlevel = "direct"\npaths = "planner/*"\n',
                       roster=[ALICE])
    activity.write_rows(claim / "evidence/index/activity.csv", [
        activity.make_row(source="gh", key="a" * 40, kind="commit", person="alice", actor_raw="alice",
                          ts=datetime.fromisoformat("2026-09-02T12:00:00+00:00"), paths=["planner/a.py"], raw_path="x"),
        activity.make_row(source="gh", key="b" * 40, kind="commit", person="alice", actor_raw="alice",
                          ts=datetime.fromisoformat("2026-10-02T12:00:00+00:00"), paths=["web/a.py"], raw_path="x")])
    timebasis.run(claim, preliminary=True)
    before = (claim / "scope/preliminary/maximum/person_summary.csv").read_bytes()
    fin = claim / "financials"
    fin.mkdir()
    (fin / "classification_overrides.csv").write_text(
        "source,key,project,level,category,classified_by,confidence,reason\ngh," + "b" * 40 + ",P1,direct,,claimant,1,experiment\n")
    (fin / "gap_months.csv").write_text("person,month,basis,basis_source,corroborated,basis_share\nalice,2026-11,reviews,cal,Y,80\n")
    timebasis.run(claim, preliminary=True)
    assert (claim / "scope/preliminary/maximum/person_summary.csv").read_bytes() == before


# Finding 2: hand-written gaps.md notes are kept and the generated sections still appear

def test_gaps_notes_written_early_are_kept_and_generated_sections_added(make_claim):
    claim = make_claim(roster=[ALICE])
    (claim / "scope").mkdir()
    (claim / "scope/projects.toml").write_text('[[project]]\nid = "P1"\ntitle = "T"\n')
    (claim / "draft/P1").mkdir(parents=True)
    (claim / "draft/P1/narrative.md").write_text("# P1: T\n\n## Line 242\nx\n")
    (claim / "financials").mkdir()
    (claim / "financials/person_summary.csv").write_text("person,confirmed_pct,flags\nalice,50,SPARSE_EVIDENCE\n")
    (claim / "STATE.md").write_text("## Locked decisions\n- D1\n\n## Open questions for the claimant\n- Q1 (blocks phase 7): invoices\n")
    (claim / "handoff").mkdir()
    (claim / "handoff/gaps.md").write_text("# Gaps and follow-ups\n\nCarried from review round 2: trial counts unrecorded.\n")
    handoff.build(claim)
    handoff.build(claim)  # idempotent: the generated block is replaced, not duplicated
    text = (claim / "handoff/gaps.md").read_text()
    assert "Carried from review round 2" in text and "Q1 (blocks phase 7): invoices" in text and "alice: SPARSE_EVIDENCE" in text
    assert text.count("Q1 (blocks phase 7)") == 1


# Finding 3: a fresh template does not hide blocking unknowns

def test_fresh_template_reports_fiscal_year_and_first_claim(tmp_path):
    shutil.copy(TEMPLATES / "sred.toml", tmp_path / "sred.toml")
    shutil.copy(TEMPLATES / "roster.csv", tmp_path / "roster.csv")
    missing, info = setupcheck.check_setup(tmp_path)
    text = "\n".join(map(str, missing))
    assert "fiscal_year" in text and "claim.first_claim" in text
    assert not any("Filing deadline" in line for line in info)


# Finding 4: project ids in rules and overrides must exist in scope/projects.toml

def test_handoff_flags_rules_and_overrides_naming_unknown_projects(make_claim):
    claim = make_claim('[[classification.rules]]\nid = "r1"\nproject = "P9"\nlevel = "direct"\npaths = "x/*"\n', roster=[ALICE])
    (claim / "scope").mkdir()
    (claim / "scope/projects.toml").write_text('[[project]]\nid = "P1"\ntitle = "T"\n')
    (claim / "financials").mkdir()
    (claim / "financials/classification_overrides.csv").write_text(
        "source,key,project,level,category,classified_by,confidence,reason\ngh,k1,P7,support,,claude,0.9,r\n")
    messages = [f.message for f in handoff.check(claim)]
    assert any("P9" in m and "classification rule r1" in m for m in messages)
    assert any("P7" in m and "classification_overrides.csv" in m for m in messages)
