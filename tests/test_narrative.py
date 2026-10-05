import csv
import re

import pytest

import check
from sredlib import config
from sredlib.narrative import check_narrative, line_count, load_patterns, parse_narrative, word_count

CLAIM_TOML = """
[claim]
prior_titles = ["Adaptive Grasp Planning Under Occlusion"]
field_codes = ["2.02.09"]
"""
SECTION_A = ("- 200 Project title: Adaptive Grasp Planning Under Occlusion\n- 202 Start date: 2026-09-02\n"
             "- 204 Completion date: 2027-07-31\n- 206 Field of science code: 2.02.09\n- 208 Continuation: yes\n- 210 First claim: no\n")
CLEAN_242 = "It was uncertain whether occlusion-aware sampling could keep grasp success above the baseline under partial visibility [C1]."
CLEAN_244 = "The team tested three sampling strategies across 230 trials [C2]. Contractor developers built the test harness."
CLEAN_246 = "The team determined that visibility-weighted sampling holds success rates under occlusion of up to 40% [C3]."
SECTION_C = "- Key individuals: Alice Chen (Lead developer)\n- Contractors: Carol Diaz (Diaz Robotics)\n"
EVIDENCE = [{"claim_id": c, "statement": "s", "source_key": "k", "raw_path": "p", "verified": "Y"} for c in ("C1", "C2", "C3")]


def text(l242=CLEAN_242, l244=CLEAN_244, l246=CLEAN_246, a=SECTION_A, c=SECTION_C):
    return (f"# P1: Adaptive Grasp Planning Under Occlusion\n\n## Section A\n{a}\n## Line 242\n{l242}\n\n---\n\n"
            f"## Line 244\n{l244}\n\n## Line 246\n{l246}\n\n## Section C\n{c}")


@pytest.fixture
def cfg(make_claim):
    return config.load_config(make_claim(CLAIM_TOML) / "sred.toml")


def run(cfg, body, evidence=EVIDENCE):
    return check_narrative(parse_narrative(body), evidence, cfg, load_patterns())


def test_parse_reads_sections_and_drops_rule_lines():
    n = parse_narrative(text())
    assert n.project == "P1" and n.title == "Adaptive Grasp Planning Under Occlusion"
    assert n.section_a["208"] == "yes" and n.section_c["contractors"] == "Carol Diaz (Diaz Robotics)"
    assert "---" not in n.lines["242"]


def test_counts_strip_markers_and_rule_lines():
    assert word_count("It was uncertain [C1] whether\n---\n") == 4
    assert line_count("Alpha beta.\n\nGamma.") == 3
    assert line_count(" ".join(["word"] * 32), width=78) == 3


def test_clean_narrative_passes(cfg):
    findings, counts = run(cfg, text())
    assert findings == []
    assert counts["242"][0] == 16


def test_word_limit_is_an_error_in_words_mode_and_a_warning_in_lines_mode(cfg):
    long = " ".join(["word"] * 351) + " [C1]."
    findings, _ = run(cfg, text(l242=long))
    assert ("error", "M-L01") in {(f.severity, f.rule) for f in findings}
    cfg["limits"] = {"mode": "lines"}
    findings, _ = run(cfg, text(l242=long))
    assert ("warning", "M-L01") in {(f.severity, f.rule) for f in findings}
    assert not any(f.severity == "error" for f in findings)


def test_markers_must_exist_and_be_verified(cfg):
    findings, _ = run(cfg, text(), evidence=[dict(EVIDENCE[0]), dict(EVIDENCE[1], verified="N")])
    msgs = [f.message for f in findings if f.rule == "EVIDENCE"]
    assert any("[C2] is not verified" in m for m in msgs) and any("[C3] has no row" in m for m in msgs)


def test_numbers_need_a_marker_but_years_do_not(cfg):
    findings, _ = run(cfg, text(l244="In 2026 the team ran 230 trials. Contractor developers built the harness [C2]."))
    hits = [f for f in findings if f.rule == "M-L14"]
    assert len(hits) == 1 and "'230'" in hits[0].message


def test_trigger_words_flagged_in_lines_and_title(cfg):
    a = SECTION_A.replace("Adaptive Grasp Planning Under Occlusion", "Grasp Planner Migration")
    findings, _ = run(cfg, text(l244="We migrated the planner to a new framework [C2]. Contractor staff helped.", a=a))
    where = {(f.rule, f.where) for f in findings}
    assert ("M-W05", "244") in where and ("M-W05", "title") in where
    assert ("M-L05", "A") in where


def test_section_a_rules(cfg):
    a = (SECTION_A.replace("2026-09-02", "2026-08-01").replace("- 210 First claim: no", "- 210 First claim: yes")
         .replace("2.02.09", "2.2.9"))
    assert {"M-L06", "M-L07", "M-L10"} <= {f.rule for f in run(cfg, text(a=a))[0]}


def test_start_before_fiscal_year_requires_continuation(cfg):
    a = (SECTION_A.replace("2026-09-02", "2026-05-01").replace("- 208 Continuation: yes", "- 208 Continuation: no")
         .replace("- 210 First claim: no", "- 210 First claim: yes"))
    findings, _ = run(cfg, text(a=a))
    assert any(f.severity == "error" and "requires Line 208" in f.message for f in findings)


def test_late_dates_and_missing_contractor_statement(cfg):
    findings, _ = run(cfg, text(l244="The team tested sampling in March 2028 [C2]."))
    assert {"M-L12", "M-L11"} <= {f.rule for f in findings}


def test_shipped_patterns_are_valid():
    patterns = load_patterns()
    ids = [p["id"] for p in patterns]
    assert len(patterns) >= 40 and len(ids) == len(set(ids))
    for p in patterns:
        re.compile(p["regex"])
        assert set(p["scope"]) <= {"242", "244", "246", "title"}
        assert p["severity"] in {"hard", "high", "med", "low", "soft"}
        assert p["hint"]


def test_cli_reports_counts_and_exit_code(make_claim, capsys):
    claim = make_claim(CLAIM_TOML)
    d = claim / "draft/P1"
    d.mkdir(parents=True)
    (d / "narrative.md").write_text(text())
    with (d / "evidence_table.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["claim_id", "statement", "source_key", "raw_path", "verified"])
        writer.writeheader()
        writer.writerows(EVIDENCE)
    assert check.main(["narrative", str(d / "narrative.md")]) == 0
    out = capsys.readouterr().out
    assert "Line 242: 16/350 words" in out and "0 errors" in out
    (d / "narrative.md").write_text(text(l242=" ".join(["word"] * 351)))
    assert check.main(["narrative", str(d / "narrative.md")]) == 1


def test_company_scoped_wording_in_242_is_flagged_low(cfg):
    l242 = "It was uncertain whether the sampler could keep success above the baseline under our constraints [C1]."
    hits = [f for f in run(cfg, text(l242=l242))[0] if f.rule == "M-W15b"]
    assert [(f.where, f.severity) for f in hits] == [("242", "info")]
