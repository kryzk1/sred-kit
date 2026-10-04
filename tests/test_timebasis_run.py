import csv
from datetime import date, datetime

import time_basis
from sredlib import activity, timebasis
from sredlib.roster import ROSTER_COLUMNS

FY = (date(2026, 8, 1), date(2027, 7, 31))


def person(**kw):
    base = {c: "" for c in ROSTER_COLUMNS}
    base.update(kw)
    return base


ALICE = person(id="alice", name="Alice Chen", classification="employee", in_canada="Y", specified_employee="N",
               aliases="email:alice@acme.test", paid_hours="2080", wages_paid="100000.00", wages_earned="100000.00")
CAROL = person(id="carol", name="Carol Diaz", classification="contractor", start="2026-09-01", end="2026-10-31",
               in_canada="Y", specified_employee="N", aliases="email:carol@diaz.test", wages_paid="50000.10",
               wages_earned="50000.10", arms_length="Y", contract_provided="Y", sred_in_contract="N")
MONTHS = {("alice", "2026-09"): {"evidence_days": 4, "sred_days": 3.0, "by_project": {}},
          ("carol", "2026-09"): {"evidence_days": 2, "sred_days": 2.0, "by_project": {}},
          ("carol", "2026-10"): {"evidence_days": 1, "sred_days": 0.0, "by_project": {}}}
GAPS = [
    {"person": "alice", "month": "2026-10", "basis": "design reviews", "basis_source": "calendar", "corroborated": "Y", "basis_share": "60"},
    {"person": "alice", "month": "2026-11", "basis": "whiteboard sessions", "basis_source": "", "corroborated": "", "basis_share": "50"},
]


def by_person(summary):
    return {s["person"]: s for s in summary}


def test_proposed_pct_depends_on_scenario():
    for scenario, expected in (("conservative", "6.25"), ("balanced", "11.25"), ("maximum", "15.42")):
        s = by_person(timebasis.summarize([ALICE, CAROL], MONTHS, GAPS, FY, scenario, []))
        assert s["alice"]["proposed_pct"] == expected
    s = by_person(timebasis.summarize([ALICE, CAROL], MONTHS, GAPS, FY, "balanced", []))
    assert (s["carol"]["months_employed"], s["carol"]["proposed_pct"], s["carol"]["evidence_share"]) == (2, "50.00", "66.67")
    assert s["alice"]["gap_months"] == 11 and "THIN_EVIDENCE" in s["carol"]["flags"]


def test_claimant_edits_survive_and_drive_flags():
    previous = [{"person": "alice", "confirmed_pct": "75%", "basis": "", "override_reason": ""},
                {"person": "carol", "confirmed_pct": "95", "basis": "", "override_reason": "contract scope"}]
    s = by_person(timebasis.summarize([ALICE, CAROL], MONTHS, GAPS, FY, "balanced", previous))
    assert s["alice"]["confirmed_pct"] == "75%"
    assert "OVERRIDE_NO_REASON" in s["alice"]["flags"] and "UNCONFIRMED" not in s["alice"]["flags"]
    assert "OVER_90_NO_BASIS" in s["carol"]["flags"] and "OVERRIDE_NO_REASON" not in s["carol"]["flags"]


def test_identical_dual_role_and_outside_canada_flags():
    bob_emp = person(id="bob", name="Bob Roy", classification="employee", in_canada="Y")
    bob_con = person(id="bob-co", name="Bob Roy", classification="contractor", in_canada="N")
    months = {("bob", "2026-09"): {"evidence_days": 1, "sred_days": 1.0, "by_project": {}},
              ("bob-co", "2026-09"): {"evidence_days": 1, "sred_days": 1.0, "by_project": {}}}
    previous = [{"person": "bob", "confirmed_pct": "80"}, {"person": "bob-co", "confirmed_pct": "80"}]
    s = by_person(timebasis.summarize([bob_emp, bob_con], months, [], FY, "balanced", previous))
    for flag in ("IDENTICAL_PCT", "DUAL_ROLE"):
        assert flag in s["bob"]["flags"] and flag in s["bob-co"]["flags"]
    assert "OUTSIDE_CANADA" in s["bob-co"]["flags"]


def test_labour_summary_amounts_and_weighted_total():
    summary = [{"person": "alice", "confirmed_pct": "75", "proposed_pct": "6.25", "basis": "weekly experiment reviews"},
               {"person": "carol", "confirmed_pct": "33.33", "proposed_pct": "50.00", "basis": ""}]
    rows = timebasis.labour_summary([ALICE, CAROL], summary, timebasis.load_columns({"_dir": "."}))
    col = {name: i for i, name in enumerate(rows[0])}
    alice, carol, total = rows[1], rows[2], rows[3]
    assert (alice[col["SRED %"]], alice[col["SRED Hours"]], alice[col["SRED Wages"]]) == ("75.00%", "1560.00", "75000.00")
    assert alice[col["Classification"]] == "Employee" and alice[col["Basis"]] == "weekly experiment reviews"
    assert (carol[col["SRED Hours"]], carol[col["SRED Wages"]], carol[col["Classification"]]) == ("", "16665.03", "Subcontractor")
    assert (total[col["Name"]], total[col["Total Wages (Earned FY)"]], total[col["SRED Wages"]], total[col["SRED %"]]) == \
        ("TOTAL", "150000.10", "91665.03", "61.11%")


def test_scenario_totals_and_itc_estimate():
    summary = [{"person": "alice", "confirmed_pct": "75", "proposed_pct": "6.25"}, {"person": "carol", "confirmed_pct": "33.33", "proposed_pct": "50"}]
    totals = timebasis.scenario_totals([ALICE, CAROL], summary, {"rates": {"itc_rate": 0.35, "proxy_rate": 0.55, "contract_rate": 0.80}})
    assert totals["employee_sred_wages"] == "75000.00" and totals["contractor_sred_amount"] == "16665.03"
    assert totals["itc_estimate"] == "45353.71" and "Estimate only" in totals["itc_note"]
    assert "itc_estimate" not in timebasis.scenario_totals([ALICE, CAROL], summary, {})


CLAIM_TOML = """
[claim]
scenario = "balanced"

[payroll]
total_wages_earned = 150000.00

[[classification.rules]]
id = "r1"
project = "P1"
level = "direct"
paths = "planner/*"
"""
OUTPUTS = ["activity_ledger.csv", "review_queue.csv", "time_basis.csv", "gap_months.csv", "person_summary.csv",
           "labour_summary.csv", "financial_checks.md", "scenario_balanced.json"]


def commit(key, who, day, path):
    return activity.make_row(source="gh", key=key, kind="commit", person=who, actor_raw=who,
                             ts=datetime.fromisoformat(f"{day}T12:00:00+00:00"), paths=[path], raw_path="evidence/raw/gh/x.json")


def setup_claim(make_claim):
    claim = make_claim(CLAIM_TOML, roster=[ALICE, CAROL])
    activity.write_rows(claim / "evidence/index/activity.csv", [
        commit("a" * 40, "alice", "2026-09-02", "planner/a.py"),
        commit("b" * 40, "alice", "2026-10-05", "web/x.py"),
        commit("c" * 40, "carol", "2026-09-10", "planner/b.py"),
    ])
    return claim


def test_run_writes_outputs_preserves_confirmations_and_is_deterministic(make_claim):
    claim = setup_claim(make_claim)
    fin = claim / "financials"
    result = timebasis.run(claim)
    assert result["scenario"] == "balanced" and result["review_queue"] == 1
    assert all((fin / name).exists() for name in OUTPUTS)
    assert "MISMATCH" in (fin / "financial_checks.md").read_text()
    first = {name: (fin / name).read_bytes() for name in OUTPUTS}
    timebasis.run(claim)
    assert {name: (fin / name).read_bytes() for name in OUTPUTS} == first
    rows = list(csv.DictReader((fin / "person_summary.csv").open()))
    rows[0]["confirmed_pct"], rows[0]["basis"] = "75%", "weekly experiment reviews"
    with (fin / "person_summary.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=timebasis.SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    timebasis.run(claim)
    again = {r["person"]: r for r in csv.DictReader((fin / "person_summary.csv").open())}
    assert again["alice"]["confirmed_pct"] == "75%" and again["alice"]["basis"] == "weekly experiment reviews"
    labour = list(csv.reader((fin / "labour_summary.csv").open()))
    assert labour[1][labour[0].index("SRED %")] == "75.00%"


def test_preliminary_run_writes_to_scope_and_leaves_financials_alone(make_claim, capsys):
    claim = setup_claim(make_claim)
    assert time_basis.main(["--claim", str(claim), "--scenario", "maximum", "--preliminary"]) == 0
    assert (claim / "scope/preliminary/maximum/person_summary.csv").exists()
    assert (claim / "scope/preliminary/maximum/scenario_maximum.json").exists()
    assert not (claim / "financials/labour_summary.csv").exists()
    assert "employee_sred_wages" in capsys.readouterr().out


def test_cli_errors_are_clear(make_claim, capsys):
    claim = make_claim("", roster=[ALICE])
    assert time_basis.main(["--claim", str(claim)]) == 2
    assert "scenario must be one of" in capsys.readouterr().err
