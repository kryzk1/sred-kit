from datetime import date

import pytest

from sredlib.timebasis import TimeBasisError, classify, employed_months, gap_share, merge_gaps, month_range, monthly

FY = (date(2026, 8, 1), date(2027, 7, 31))
RULES = [
    {"id": "r1", "project": "P1", "level": "direct", "paths": "planner/*"},
    {"id": "r2", "project": "", "level": "none", "category": "routine", "container": "acme/website"},
]


def arow(key, person="alice", day="2026-09-02", kind="commit", container="acme/vision", paths="", tags="", title="", weight="verbatim"):
    return {"source": "gh", "key": key, "kind": kind, "person": person, "date": day, "weight": weight,
            "container": container, "paths": paths, "tags": tags, "title": title}


def override(key, level, project="P1", by="claude", conf="0.9", category=""):
    return {"source": "gh", "key": key, "project": project, "level": level, "category": category,
            "classified_by": by, "confidence": conf, "reason": "r"}


def led(key, day, project="P1", level="direct", kind="commit", weight="verbatim", person="alice"):
    return {"source": "gh", "key": key, "kind": kind, "person": person, "date": day, "weight": weight,
            "project": project if level != "none" else "", "level": level}


def test_classify_precedence_and_review_queue():
    rows = [arow("k1", paths="planner/a.py"), arow("k2", container="acme/website"), arow("k3"), arow("k4"),
            arow("k5", paths="planner/b.py"), arow("k6", person="bot"), arow("k7", person="unmatched:x"), arow("k8")]
    overrides = [override("k3", "support"), override("k4", "direct", conf="0.5"),
                 override("k5", "none", project="", by="claimant", category="routine")]
    ledger = {e["key"]: e for e in classify(rows, RULES, overrides, 0.7)}
    assert set(ledger) == {"k1", "k2", "k3", "k4", "k5", "k8"}
    assert (ledger["k1"]["project"], ledger["k1"]["level"], ledger["k1"]["classified_by"]) == ("P1", "direct", "rule:r1")
    assert (ledger["k2"]["level"], ledger["k2"]["category"], ledger["k2"]["needs_review"]) == ("none", "routine", "N")
    assert (ledger["k3"]["level"], ledger["k3"]["needs_review"]) == ("support", "N")
    assert ledger["k4"]["needs_review"] == "Y"
    assert (ledger["k5"]["level"], ledger["k5"]["classified_by"]) == ("none", "claimant")
    assert (ledger["k8"]["category"], ledger["k8"]["needs_review"]) == ("unclassified", "Y")


def test_classify_rejects_bad_levels():
    with pytest.raises(TimeBasisError, match="level"):
        classify([arow("k1")], [], [override("k1", "maybe")], 0.7)
    with pytest.raises(TimeBasisError, match="needs a project"):
        classify([arow("k1")], [], [override("k1", "direct", project="")], 0.7)


def test_monthly_splits_mixed_days_by_scenario():
    ledger = [led("a", "2026-09-02"), led("b", "2026-09-02"), led("c", "2026-09-02", level="none"), led("d", "2026-09-03", level="support")]
    cons = monthly(ledger, "conservative", {})[("alice", "2026-09")]
    bal = monthly(ledger, "balanced", {})[("alice", "2026-09")]
    assert cons["evidence_days"] == 2 and round(cons["sred_days"], 3) == 0.667
    assert round(bal["sred_days"], 3) == 1.667 and round(bal["by_project"]["P1"], 3) == 1.667


def test_summary_weight_rows_excluded_only_in_conservative():
    ledger = [led("m", "2026-09-04", kind="meeting", weight="summary")]
    assert ("alice", "2026-09") not in monthly(ledger, "conservative", {})
    assert monthly(ledger, "maximum", {})[("alice", "2026-09")]["sred_days"] == 1.0


def test_kind_weights_can_zero_out_chat():
    ledger = [led("x", "2026-09-05", kind="chat_message", level="none"), led("y", "2026-09-05")]
    assert monthly(ledger, "balanced", {"chat_message": 0.0})[("alice", "2026-09")]["sred_days"] == 1.0


def test_employed_months_and_ranges():
    assert month_range(date(2026, 11, 15), date(2027, 2, 1)) == ["2026-11", "2026-12", "2027-01", "2027-02"]
    assert len(employed_months({"start": "", "end": ""}, FY)) == 12
    assert employed_months({"start": "2026-10-15", "end": ""}, FY)[0] == "2026-10"
    assert employed_months({"start": "2025-01-01", "end": "2026-06-30"}, FY) == []


def test_gap_rows_merge_and_scenario_shares():
    existing = [
        {"person": "alice", "month": "2026-10", "basis": "design reviews", "basis_source": "calendar", "corroborated": "Y", "basis_share": "60"},
        {"person": "alice", "month": "2026-09", "basis": "stale", "basis_source": "", "corroborated": "", "basis_share": "10"},
    ]
    rows, leftovers = merge_gaps(existing, [("alice", "2026-10"), ("alice", "2026-11")])
    assert [g["basis"] for g in leftovers] == ["stale"]
    assert [r["month"] for r in rows] == ["2026-10", "2026-11"]
    assert rows[0]["basis"] == "design reviews" and rows[1]["basis"] == ""
    corroborated, asserted = rows[0], dict(rows[0], corroborated="")
    assert gap_share(corroborated, "conservative") == 0.0
    assert gap_share(corroborated, "balanced") == 0.6 and gap_share(asserted, "balanced") == 0.0
    assert gap_share(asserted, "maximum") == 0.6
    with pytest.raises(TimeBasisError, match="basis_share"):
        gap_share(dict(rows[0], basis_share="lots"), "maximum")
