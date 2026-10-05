import json
from datetime import datetime, timezone

from sredlib import manifest


def test_record_writes_checksums_and_replaces_source_entry(tmp_path):
    f = tmp_path / "evidence/raw/gh/a.json"
    f.parent.mkdir(parents=True)
    f.write_text("abc")
    now = datetime(2027, 8, 2, 9, tzinfo=timezone.utc)
    manifest.record(tmp_path, "gh", method="api", files=[f], counts={"pulls": 1}, date_range=("2026-08-01", "2027-07-31"), now=now)
    manifest.record(tmp_path, "gh", method="api", files=[f], counts={"pulls": 2}, now=now)
    entry = json.loads((tmp_path / "evidence/raw/MANIFEST.json").read_text())["sources"]["gh"]
    assert entry["counts"] == {"pulls": 2}
    assert entry["files"][0] == {"path": "evidence/raw/gh/a.json", "bytes": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}
    assert entry["captured_at"] == "2027-08-02T09:00:00+00:00"
    assert entry["date_range"] is None
