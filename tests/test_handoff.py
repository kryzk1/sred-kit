import csv

import check
import handoff as handoff_cli
from sredlib import handoff, timebasis

PROJECTS = """
[[project]]
id = "P1"
title = "Adaptive Grasp Planning Under Occlusion"
start = 2026-09-02
end = 2027-07-31
continuation = true
field_code = "2.02.09"
"""
NARRATIVE = """# P1: Adaptive Grasp Planning Under Occlusion

## Section A
- 200 Project title: Adaptive Grasp Planning Under Occlusion
- 202 Start date: 2026-09-02
- 204 Completion date: 2027-07-31
- 206 Field of science code: 2.02.09
- 208 Continuation: yes
- 210 First claim: no

## Line 242
It was uncertain whether occlusion-aware sampling could keep grasp success above the baseline [C1].

## Line 244
The team tested three sampling strategies across 230 trials [C2]. Contractor developers built the harness.

## Line 246
The team determined that visibility-weighted sampling holds success under 40% occlusion [C3].

## Section C
- Key individuals: Alice Chen (Lead developer)
- Contractors: Carol Diaz (Diaz Robotics)
"""
STATE = """# SR&ED claim state: Acme Robotics Inc. FY2027
phase: 7-handoff

## Locked decisions
- D1 (2027-08-05, ratified by CEO): scenario = balanced; project P1

## Open questions for the claimant
- Q1: confirm the contractor's final invoice

## Phase log
- 2027-08-02 capture complete
"""
ROSTER = [{"id": "alice", "name": "Alice Chen", "classification": "employee"}, {"id": "carol", "name": "Carol Diaz", "classification": "contractor"}]


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make(make_claim, alice_pct="75", carol_pct="33.33", narrative=NARRATIVE, projects=PROJECTS):
    claim = make_claim(roster=ROSTER)
    (claim / "scope").mkdir()
    (claim / "scope/projects.toml").write_text(projects)
    (claim / "draft/P1").mkdir(parents=True)
    (claim / "draft/P1/narrative.md").write_text(narrative)
    write_csv(claim / "draft/P1/evidence_table.csv", ["claim_id", "statement", "source_key", "raw_path", "verified"],
              [{"claim_id": f"C{i}", "statement": f"s{i}", "source_key": f"k{i}", "raw_path": "evidence/raw/gh/x.json", "verified": "Y"} for i in range(1, 5)])
    write_csv(claim / "financials/person_summary.csv", timebasis.SUMMARY_COLUMNS,
              [{"person": "alice", "confirmed_pct": alice_pct}, {"person": "carol", "confirmed_pct": carol_pct}])
    shown = [f"{name},{float(pct):.2f}%" for name, pct in (("Alice Chen", alice_pct), ("Carol Diaz", carol_pct)) if pct]
    (claim / "financials/labour_summary.csv").write_text("Name,SRED %\n" + "\n".join(shown) + "\n")
    (claim / "STATE.md").write_text(STATE)
    return claim


def test_build_then_check_passes_once_readme_exists(make_claim):
    claim = make(make_claim)
    written = handoff.build(claim)
    out = claim / "handoff"
    assert set(written) == {"T661-Part2-P1.md", "evidence_index.csv", "labour_summary.csv", "decision_log.md", "gaps.md"}
    t661 = (out / "T661-Part2-P1.md").read_text()
    assert "[C" not in t661 and "Lengths: Line 242 " in t661 and "Line 246" in t661
    index = list(csv.DictReader((out / "evidence_index.csv").open()))
    assert [r["claim_id"] for r in index] == ["C1", "C2", "C3"] and index[0]["project"] == "P1"
    assert "D1 (2027-08-05" in (out / "decision_log.md").read_text()
    assert "Q1: confirm the contractor" in (out / "gaps.md").read_text()
    assert [f.message for f in handoff.check(claim)] == ["missing README.md"]
    (out / "README.md").write_text("# For the accountant\n")
    assert handoff.check(claim) == []


def test_gaps_file_is_never_overwritten(make_claim):
    claim = make(make_claim)
    (claim / "handoff").mkdir()
    (claim / "handoff/gaps.md").write_text("edited by hand\n")
    assert "gaps.md" not in handoff.build(claim)
    assert (claim / "handoff/gaps.md").read_text() == "edited by hand\n"


def test_consistency_errors(make_claim):
    narrative = NARRATIVE.replace("Carol Diaz (Diaz Robotics)", "Dana Wu (Wu Labs)")
    claim = make(make_claim, alice_pct="0", carol_pct="", narrative=narrative, projects=PROJECTS.replace("Under Occlusion", "In Clutter"))
    handoff.build(claim)
    (claim / "handoff/README.md").write_text("x")
    messages = [f.message for f in handoff.check(claim) if f.severity == "error"]
    assert any("Section A Line 200" in m for m in messages)
    assert any("'Dana Wu', who is not in roster.csv" in m for m in messages)
    assert any("Alice Chen is named in Section C but has 0% SR&ED time" in m for m in messages)
    assert any("carol: SR&ED % is not confirmed" in m for m in messages)


def test_markers_left_in_handoff_are_an_error(make_claim):
    claim = make(make_claim)
    handoff.build(claim)
    (claim / "handoff/README.md").write_text("x")
    (claim / "handoff/T661-Part2-P1.md").write_text("text [C9]")
    assert any("claim markers left" in f.message for f in handoff.check(claim))


def test_clis(make_claim, capsys):
    claim = make(make_claim)
    assert handoff_cli.main(["build", "--claim", str(claim)]) == 0
    assert check.main(["handoff", "--claim", str(claim)]) == 1
    (claim / "handoff/README.md").write_text("x")
    assert check.main(["handoff", "--claim", str(claim)]) == 0
    assert "0 errors" in capsys.readouterr().out
