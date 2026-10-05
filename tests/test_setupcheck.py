from datetime import date

import check
from sredlib import setupcheck

COMPLETE = """
[claim]
first_claim = false
prior_filings = ["prior/FY2026.pdf"]
prior_titles = ["Adaptive Grasp Planning Under Occlusion"]

[preparer]
accountant = "Pat Lee"
ratifier = "CEO"

[eligibility]
government_assistance = "none"
client_contract_work = "none"
funded_by_others = "none"
work_outside_canada = "none"

[payroll]
total_wages_earned = 150000.10

[limits]
mode = "words"

[[sources]]
name = "jira"
kind = "tracker"
tool = "jira"
method = "export"
export_path = "exports/jira.csv"
mapping = "jira-csv"

[[sources]]
name = "code"
kind = "code"
method = "git-log"
paths = ["clones/vision"]
"""
ROSTER = [
    {"id": "alice", "name": "Alice Chen", "classification": "employee", "aliases": "email:alice@acme.test",
     "in_canada": "Y", "specified_employee": "N", "paid_hours": "2080", "wages_earned": "100000.00"},
    {"id": "carol", "name": "Carol Diaz", "classification": "contractor", "aliases": "email:carol@diaz.test",
     "in_canada": "Y", "specified_employee": "N", "wages_earned": "50000.10", "arms_length": "Y", "contract_provided": "Y", "sred_in_contract": "N"},
]


def build(make_claim, toml=COMPLETE, roster=ROSTER):
    claim = make_claim(toml, roster=roster)
    for rel in ("prior/FY2026.pdf", "exports/jira.csv"):
        (claim / rel).parent.mkdir(parents=True, exist_ok=True)
        (claim / rel).write_text("x")
    return claim


def deferred(make_claim):
    """Onboarding finished with two 'I don't know yet' answers."""
    return build(make_claim, COMPLETE.replace("total_wages_earned = 150000.10", "total_wages_earned = 0.0"),
                 [dict(ROSTER[0], paid_hours=""), ROSTER[1]])


def test_complete_claim_has_nothing_missing(make_claim):
    missing, info = setupcheck.check_setup(build(make_claim))
    assert missing == []
    assert info == ["Filing deadline: 2029-01-31 (fiscal year end + 18 months)"]


def test_two_deferred_items_are_reported_with_their_phase(make_claim):
    missing, _ = setupcheck.check_setup(deferred(make_claim))
    assert [str(m) for m in missing] == [
        "MISSING [phase 6] roster.csv alice: paid_hours",
        "MISSING [phase 6] sred.toml: payroll.total_wages_earned: employees' earned wages for the fiscal year from payroll (contractors excluded), to reconcile the roster",
    ]


def test_empty_claim_lists_everything_by_phase(make_claim):
    missing, _ = setupcheck.check_setup(make_claim(roster=[]))
    text = "\n".join(map(str, missing))
    assert {m.phase for m in missing} == {2, 3, 6, 7}
    for needle in ['kind = "code"', "no people listed", "claim.first_claim", "eligibility.government_assistance",
                   "preparer.ratifier", "payroll.total_wages_earned", "preparer.accountant", "limits.mode"]:
        assert needle in text


def test_api_source_needs_its_credentials(make_claim, monkeypatch):
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    claim = make_claim('[[sources]]\nname = "gl"\nkind = "code"\ntool = "gitlab"\nmethod = "api"\n', roster=ROSTER)
    text = "\n".join(map(str, setupcheck.check_setup(claim)[0]))
    assert "environment variable GITLAB_TOKEN is not set" in text and "gl: projects" in text


def test_add_months_clamps_to_month_end():
    assert setupcheck.add_months(date(2027, 8, 31), 18) == date(2029, 2, 28)
    assert setupcheck.filing_deadline(date(2027, 7, 31)) == date(2029, 1, 31)


def test_cli_gates_on_current_phase(make_claim, capsys):
    claim = deferred(make_claim)
    assert check.main(["setup", "--claim", str(claim)]) == 0
    (claim / "STATE.md").write_text("# state\nphase: 6-financials\n")
    assert check.main(["setup", "--claim", str(claim)]) == 1
    assert "2 missing; 2 block phase 6." in capsys.readouterr().out
    assert check.main(["setup", "--claim", str(claim), "--phase", "3"]) == 0


def test_captured_api_source_no_longer_needs_credentials(make_claim, monkeypatch):
    from sredlib import manifest

    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    claim = make_claim('[[sources]]\nname = "gl"\nkind = "code"\ntool = "gitlab"\nmethod = "api"\nprojects = ["acme/vision"]\n', roster=ROSTER)
    raw = claim / "evidence/raw/gl/acme__vision.json"
    raw.parent.mkdir(parents=True)
    raw.write_text("{}")
    manifest.record(claim, "gl", method="api", files=[raw], counts={"merge_requests": 0})
    assert "GITLAB_TOKEN" not in "\n".join(map(str, setupcheck.check_setup(claim)[0]))
