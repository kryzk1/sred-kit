from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sredlib import activity

TS = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
FY = (date(2026, 8, 1), date(2027, 7, 31))


def row(**kw):
    base = dict(source="gh", key="acme/vision#1", kind="pr_opened", person="alice", actor_raw="achen", ts=TS, raw_path="evidence/raw/gh/x.json")
    base.update(kw)
    return activity.make_row(**base)


def test_make_row_truncates_and_joins():
    r = row(excerpt="x" * 600, tags=["a", "b", "a", ""], paths=[f"p{i}" for i in range(60)], title="\n  First line\nsecond")
    assert r["excerpt"].endswith(activity.TRUNC) and len(r["excerpt"]) == 500 + len(activity.TRUNC)
    assert r["tags"] == "a;b"
    assert r["paths"].count(";") == 50 and r["paths"].endswith(activity.TRUNC)
    assert r["title"] == "First line"
    assert r["date"] == "2026-09-01" and r["timestamp"] == "2026-09-01T10:00:00Z"


def test_local_date_and_window_follow_company_timezone():
    van = ZoneInfo("America/Vancouver")
    late = datetime(2027, 8, 1, 5, tzinfo=timezone.utc)  # 22:00 on July 31 in Vancouver
    r = row(ts=late, tz=van)
    assert r["date"] == "2027-07-31" and r["timestamp"] == "2027-08-01T05:00:00Z"
    assert activity.in_window(late, *FY, van)
    assert not activity.in_window(late, *FY)


def test_extract_refs_finds_keys_and_pr_urls_but_not_self():
    text = "Fixes ACME-12 and ACME-12, see https://github.com/acme/vision/pull/7 and https://gitlab.com/acme/ml/core/-/merge_requests/3"
    assert activity.extract_refs(text, [r"[A-Z]+-\d+"], own_key="ACME-99") == ["ACME-12", "acme/vision#7", "acme/ml/core!3"]
    assert activity.extract_refs("ACME-1", [r"[A-Z]+-\d+"], own_key="ACME-1") == []


def test_write_read_roundtrip_is_sorted(tmp_path):
    rows = [row(key="b", ts=datetime(2026, 9, 2, tzinfo=timezone.utc)), row(key="a")]
    activity.write_rows(tmp_path / "a.csv", rows)
    header, back = activity.read_rows(tmp_path / "a.csv")
    assert header == activity.COLUMNS
    assert [r["key"] for r in back] == ["a", "b"]


def test_validate_catches_each_problem(tmp_path):
    raw = tmp_path / "evidence/raw/gh/x.json"
    raw.parent.mkdir(parents=True)
    raw.write_text("{}")
    good = row()
    bad = dict(good, key="k2", kind="nope", weight="loud", person="Not Valid!", date="2025-01-01", raw_path="missing.json")
    problems = activity.validate_rows([good, dict(good), bad], activity.COLUMNS, *FY, tmp_path, roster_ids={"alice"})
    text = "\n".join(problems)
    for needle in ["duplicate source+key", "unknown kind", "weight must be", "person must be", "outside the fiscal year", "does not exist"]:
        assert needle in text
    assert activity.validate_rows([good], ["wrong"], *FY, tmp_path) == ["columns must be exactly: " + ",".join(activity.COLUMNS)]


def test_validate_flags_person_not_in_roster(tmp_path):
    raw = tmp_path / "evidence/raw/gh/x.json"
    raw.parent.mkdir(parents=True)
    raw.write_text("{}")
    problems = activity.validate_rows([row(person="zed")], activity.COLUMNS, *FY, tmp_path, roster_ids={"alice"})
    assert problems == ["line 2 (gh:acme/vision#1): person 'zed' is not in roster.csv"]
