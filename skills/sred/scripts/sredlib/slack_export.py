"""Slack's official workspace export (zip or unzipped folder) to activity rows."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import activity
from .mapping import ImportResult
from .roster import Resolver

DAY_FILE_RE = re.compile(r"^(?:.*/)?([^/]+)/(\d{4}-\d{2}-\d{2})\.json$")
SKIP_SUBTYPES = {"channel_join", "channel_leave", "channel_topic", "channel_purpose", "channel_name", "channel_archive",
                 "bot_add", "bot_remove", "pinned_item", "group_join", "group_leave"}


def _members(path: Path) -> dict[str, bytes]:
    if path.is_dir():
        return {p.relative_to(path).as_posix(): p.read_bytes() for p in sorted(path.rglob("*.json"))}
    with zipfile.ZipFile(path) as zf:
        return {n: zf.read(n) for n in sorted(zf.namelist()) if n.endswith(".json")}


def import_slack(export_path, *, source, resolver: Resolver, regexes, claim_dir, fy, tz=None) -> ImportResult:
    export_path = Path(export_path)
    members = _members(export_path)
    result = ImportResult()
    users: dict[str, tuple[str, str]] = {}
    for name, blob in members.items():
        if name.rsplit("/", 1)[-1] == "users.json":
            for u in json.loads(blob):
                profile = u.get("profile") or {}
                users[u.get("id", "")] = (profile.get("email", ""), profile.get("real_name", "") or u.get("real_name", ""))
    raw_path = str(export_path.resolve().relative_to(Path(claim_dir).resolve()))
    start, end = fy
    for name, blob in members.items():
        m = DAY_FILE_RE.match(name)
        if not m:
            continue
        channel = m.group(1)
        try:
            messages = json.loads(blob)
        except json.JSONDecodeError as exc:
            result.failures.append(f"{name}: {exc}")
            continue
        for msg in messages:
            subtype = msg.get("subtype", "")
            if subtype in SKIP_SUBTYPES or not msg.get("ts"):
                continue
            ts = datetime.fromtimestamp(float(msg["ts"]), tz=timezone.utc)
            if not activity.in_window(ts, start, end, tz):
                result.skipped_outside_fy += 1
                continue
            user = msg.get("user", "")
            email, real = users.get(user, ("", ""))
            profile_name = (msg.get("user_profile") or {}).get("real_name", "")
            if msg.get("bot_id") or subtype == "bot_message":
                person = "bot"
            else:
                person = resolver.resolve("slack", user, email=email, name=real or profile_name)
            tags = []
            if msg.get("thread_ts"):
                tags.append(f"thread:{msg['thread_ts']}")
                if msg["thread_ts"] == msg["ts"]:
                    tags.append("thread_root")
            text = msg.get("text", "")
            result.rows.append(activity.make_row(
                source=source, key=f"{channel}:{msg['ts']}", kind="meeting" if subtype == "huddle_thread" else "chat_message",
                person=person, actor_raw=user or msg.get("username", ""), ts=ts, container=channel, tags=tags,
                title=text, excerpt=text, refs=activity.extract_refs(text, regexes), raw_path=raw_path, tz=tz,
            ))
    return result
