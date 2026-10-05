import json
import zipfile
from datetime import date

import pytest

from sredlib.mapping import PRESET_DIR, import_export, load_mapping
from sredlib.roster import Resolver

FY = (date(2026, 8, 1), date(2027, 7, 31))
ROSTER = [
    {"id": "alice", "name": "Alice Chen", "aliases": "email:alice@acme.test"},
    {"id": "bob", "name": "Bob Roy", "aliases": "email:bob@acme.test"},
]
# 2026-09-01T10:00:00Z = 1788256800; 2026-06-01T08:00:00Z = 1780300800


def make_export(tmp_path):
    zpath = tmp_path / "evidence/raw/slack/export.zip"
    zpath.parent.mkdir(parents=True)
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("users.json", json.dumps([
            {"id": "U01", "profile": {"email": "alice@acme.test", "real_name": "Alice Chen"}},
            {"id": "U02", "profile": {"real_name": "Bob Roy"}},
        ]))
        zf.writestr("channels.json", "[]")
        zf.writestr("dev/2026-09-01.json", json.dumps([
            {"type": "message", "user": "U01", "text": "Occlusion test failed, see ACME-12 and https://github.com/acme/vision/pull/7",
             "ts": "1788256800.000100", "thread_ts": "1788256800.000100", "reply_count": 1},
            {"type": "message", "user": "U02", "text": "Try the depth prior", "ts": "1788257000.000200", "thread_ts": "1788256800.000100"},
            {"type": "message", "subtype": "channel_join", "user": "U02", "text": "joined", "ts": "1788257100.000300"},
            {"type": "message", "bot_id": "B1", "text": "Deploy finished", "ts": "1788257200.000400"},
        ]))
        zf.writestr("dev/2026-06-01.json", json.dumps([{"type": "message", "user": "U01", "text": "old", "ts": "1780300800.000000"}]))
    return zpath


def run(spec, path, tmp_path, regexes=(r"[A-Z]+-\d+",)):
    return import_export(load_mapping(spec, tmp_path), path, source="src", resolver=Resolver(ROSTER), regexes=list(regexes), claim_dir=tmp_path, fy=FY)


def stage(tmp_path, fixtures, name):
    target = tmp_path / "evidence/raw/src" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((fixtures / "exports" / name).read_bytes())
    return target


def test_slack_export_messages_threads_bots_and_skips(tmp_path):
    res = run("slack-export", make_export(tmp_path), tmp_path)
    rows = {r["key"]: r for r in res.rows}
    assert set(rows) == {"dev:1788256800.000100", "dev:1788257000.000200", "dev:1788257200.000400"}
    root = rows["dev:1788256800.000100"]
    assert root["person"] == "alice" and root["date"] == "2026-09-01" and root["container"] == "dev"
    assert root["tags"] == "thread:1788256800.000100;thread_root"
    assert root["refs"] == "ACME-12;acme/vision#7"
    assert rows["dev:1788257000.000200"]["person"] == "bob"
    assert rows["dev:1788257200.000400"]["person"] == "bot"
    assert res.skipped_outside_fy == 1


def test_slack_export_unzipped_folder_without_users_file(tmp_path):
    d = tmp_path / "evidence/raw/slack/export"
    (d / "dev").mkdir(parents=True)
    (d / "dev/2026-09-01.json").write_text(json.dumps([{"type": "message", "user": "U9", "text": "hi", "ts": "1788256800.000100"}]))
    res = run("slack-export", d, tmp_path, regexes=())
    assert [r["person"] for r in res.rows] == ["unmatched:U9"]


def test_asana_preset(tmp_path, fixtures):
    res = run("asana-csv", stage(tmp_path, fixtures, "asana.csv"), tmp_path)
    created = next(r for r in res.rows if r["key"] == "1203")
    assert (created["person"], created["date"], created["container"]) == ("alice", "2026-09-14", "Grasping")


def test_clickup_preset_epoch_ms_and_first_of_several_assignees(tmp_path, fixtures):
    res = run("clickup-csv", stage(tmp_path, fixtures, "clickup.csv"), tmp_path)
    created = next(r for r in res.rows if r["key"] == "86b1x")
    assert (created["person"], created["date"], created["container"]) == ("alice", "2026-09-10", "Control")


def test_shortcut_preset(tmp_path, fixtures):
    res = run("shortcut-csv", stage(tmp_path, fixtures, "shortcut.csv"), tmp_path)
    by_key = {r["key"]: r for r in res.rows}
    assert (by_key["512"]["person"], by_key["512"]["date"]) == ("bob", "2026-11-03")
    assert by_key["512:started"]["person"] == "alice"


def test_azure_devops_preset_name_and_email_form(tmp_path, fixtures):
    res = run("azure-devops-csv", stage(tmp_path, fixtures, "azure.csv"), tmp_path)
    by_key = {r["key"]: r for r in res.rows}
    assert (by_key["4411"]["person"], by_key["4411"]["date"]) == ("bob", "2026-12-01")
    assert (by_key["4411:issue_resolved"]["person"], by_key["4411:issue_resolved"]["date"]) == ("alice", "2026-12-09")


@pytest.mark.parametrize("preset", sorted(p.stem for p in PRESET_DIR.glob("*.toml")))
def test_every_preset_loads(tmp_path, preset):
    assert load_mapping(preset, tmp_path)["tool"]
