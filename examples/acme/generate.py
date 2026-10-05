#!/usr/bin/env python3
"""Regenerate the Acme example's raw evidence and exports. Deterministic: no randomness, no network.

  python3 examples/acme/generate.py [--out DIR]

Writes evidence/raw/gitlab/*.json (the shape `capture.py gitlab` produces), evidence/raw/MANIFEST.json,
exports/jira.csv (the `jira-csv` preset format) and exports/slack/ (a Slack workspace export folder).
Everything is fictional.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo("America/Vancouver")
PEOPLE = {  # roster id: (GitLab handle, display name, email, Slack id)
    "alice": ("achen", "Alice Chen", "alice@acme.test", "U0ACHEN"),
    "bob": ("broy", "Bob Roy", "bob@acme.test", "U0BROY"),
    "dana": ("dwu", "Dana Wu", "dana@acme.test", "U0DWU"),
    "carol": ("cdiaz", "Carol Diaz", "carol@diaz.test", "U0CDIAZ"),
    "renovate": ("renovate[bot]", "renovate[bot]", "bot@renovateapp.com", ""),
}

MRS: dict[str, list[dict]] = {"acme/vision": [], "acme/website": []}
COMMITS: dict[str, list[dict]] = {"acme/vision": [], "acme/website": []}
ISSUES: list[dict] = []
SLACK: dict[str, list[dict]] = {}


def t(local: str) -> datetime:
    return datetime.strptime(local, "%Y-%m-%d %H:%M").replace(tzinfo=LOCAL)


def utc(local: str) -> str:
    return t(local).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def sha(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def gl_commit(project: str, who: str, local: str, message: str) -> dict:
    _, name, email, _ = PEOPLE[who]
    cid = sha(project, local, message)
    return {"id": cid, "title": message.splitlines()[0], "message": message, "author_name": name, "author_email": email,
            "authored_date": utc(local), "created_at": utc(local), "web_url": f"https://gitlab.com/{project}/-/commit/{cid}"}


def commit(project: str, who: str, local: str, message: str) -> None:
    COMMITS[project].append(gl_commit(project, who, local, message))


def mr(project, iid, who, opened, title, description, files, branch, labels=(), merged=None, notes=(), commits=()):
    note_rows = [{"id": iid * 100 + i, "system": False, "body": body, "author": {"username": PEOPLE[n][0]}, "created_at": utc(when)}
                 for i, (n, when, body) in enumerate(notes, start=1)]
    if merged:
        note_rows.append({"id": iid * 100 + 99, "system": True, "body": "merged", "author": {"username": PEOPLE[who][0]}, "created_at": utc(merged)})
    MRS[project].append({
        "iid": iid, "title": title, "description": description, "author": {"username": PEOPLE[who][0]},
        "created_at": utc(opened), "merged_at": utc(merged) if merged else None,
        "web_url": f"https://gitlab.com/{project}/-/merge_requests/{iid}", "source_branch": branch, "labels": list(labels),
        "_notes": note_rows, "_commits": [gl_commit(project, c, when, msg) for c, when, msg in commits], "_files": list(files),
    })


def issue(key, summary, kind, reporter, created, assignee, description, labels=(), resolved=None, comments=()):
    ISSUES.append({"key": key, "summary": summary, "kind": kind, "reporter": reporter, "created": created, "assignee": assignee,
                   "description": description, "labels": list(labels), "resolved": resolved, "comments": list(comments)})


def slack(channel, who, local, text, replies=()):
    ts = f"{int(t(local).timestamp())}.000100"
    msg = {"type": "message", "user": PEOPLE[who][3], "text": text, "ts": ts, "user_profile": {"real_name": PEOPLE[who][1]}}
    if replies:
        msg.update(thread_ts=ts, reply_count=len(replies))
    SLACK.setdefault(channel, []).append(msg)
    for r_who, r_local, r_text in replies:
        SLACK[channel].append({"type": "message", "user": PEOPLE[r_who][3], "text": r_text, "ts": f"{int(t(r_local).timestamp())}.000200",
                               "thread_ts": ts, "user_profile": {"real_name": PEOPLE[r_who][1]}})


def year() -> None:
    V, W = "acme/vision", "acme/website"

    # P1: Adaptive Grasp Planning Under Occlusion (continuing project)
    issue("ACME-101", "Re-baseline grasp success under occlusion", "Story", "alice", "2025-08-12 09:00", "alice",
          "Hypothesis: visibility-weighted sampling keeps grasp success above 80% up to 40% occlusion. Last year's results stopped at 30% occlusion on opaque parts (ACME-88).",
          labels=["research", "grasping"], resolved="2025-09-04 16:00",
          comments=[("alice", "2025-08-26 14:00", "Baseline at 20% occlusion: 86% success over 40 trials."),
                    ("dana", "2025-08-28 11:00", "Agreed to extend the trials to 60% occlusion.")])
    mr(V, 12, "alice", "2025-08-19 10:00", "Occlusion test harness for 20/40/60% scenes",
       "Builds the bin-scene harness for this year's occlusion trials. Scenes render at 20, 40 and 60% occlusion with fixed seeds so runs repeat exactly.",
       ["planner/harness.py", "tests/test_harness.py"], "feat/occlusion-harness", labels=["research"], merged="2025-08-22 15:00",
       notes=[("dana", "2025-08-20 09:30", "Is 60% occlusion realistic for mixed bins? Asking for the experiment plan.")],
       commits=[("alice", "2025-08-19 09:40", "Render bin scenes at fixed occlusion levels"),
                ("alice", "2025-08-21 16:10", "Seed scene generator for repeatable trials")])
    mr(V, 14, "carol", "2025-09-08 11:00", "Parametrize harness occlusion levels",
       "Occlusion level and part class become harness parameters so the same scene set runs across samplers.",
       ["planner/harness.py"], "feat/harness-params", labels=["research"], merged="2025-09-11 15:00",
       notes=[("alice", "2025-09-09 10:00", "Seed handling needs a fix for repeatable runs.")],
       commits=[("carol", "2025-09-08 10:30", "Expose occlusion level and part class as parameters")])
    slack("dev", "alice", "2025-09-15 10:30",
          "Visibility-weighted sampling drops to 61% at 60% occlusion. The decline isn't gradual: failures cluster on thin metal and transparent parts.",
          replies=[("carol", "2025-09-15 10:52", "Thin parts barely return depth points at that occlusion. Try a learned depth prior for those classes?"),
                   ("alice", "2025-09-15 11:05", "Yes, open a branch and track it under ACME-118.")])
    issue("ACME-118", "Test a depth prior for thin and transparent parts", "Story", "alice", "2025-09-22 09:15", "carol",
          "Hypothesis: a depth prior learned from complete scans fills missing returns on thin parts and lifts success at 60% occlusion.",
          labels=["research", "grasping"], resolved="2025-10-20 15:00",
          comments=[("carol", "2025-10-06 13:00", "Depth prior lifts thin metal parts from 52% to 74% at 60% occlusion."),
                    ("alice", "2025-10-14 10:20", "It overfits: transparent parts fall from 49% to 38%. Keeping visibility weighting for the transparent class."),
                    ("carol", "2025-10-15 09:00", "Confirmed on a second scene set, same pattern.")])
    slack("research", "dana", "2025-09-25 16:00",
          "Weekly experiment review: the P1 baseline holds to 40% occlusion; thin and transparent parts are the open question. Depth prior experiment approved.")
    commit(V, "alice", "2025-09-30 11:00", "CI: cache pip downloads")
    mr(V, 19, "carol", "2025-10-01 10:00", "Depth prior sampler (experimental)",
       "Adds a depth-completion prior ahead of grasp sampling. Results are tracked in ACME-118.",
       ["planner/depth_prior.py", "models/depth_prior.yaml"], "exp/depth-prior", labels=["research"],
       notes=[("alice", "2025-10-14 10:30", "Closing without merge: the prior overfits on transparent parts (ACME-118).")],
       commits=[("carol", "2025-10-01 09:45", "Depth completion prior for sparse parts"),
                ("carol", "2025-10-05 15:30", "Train the prior on complete scans")])
    slack("research", "dana", "2025-10-23 16:00",
          "Weekly review: depth prior rejected for transparent parts. Next: class-conditioned sampling that mixes both approaches.")
    mr(V, 23, "alice", "2025-11-05 09:30", "Hybrid sampler: class-conditioned weighting",
       "Uses the depth prior only for thin opaque parts and visibility weighting elsewhere. Across 230 grasp trials, the hybrid sampler held 79% "
       "success at 40% occlusion and 66% at 60%; transparent parts remain the limiting class at 51% at 60% occlusion.",
       ["planner/hybrid.py", "planner/harness.py"], "feat/hybrid-sampler", labels=["research"], merged="2025-11-12 14:00",
       notes=[("carol", "2025-11-06 10:00", "Ran the 60% set twice; variance under 3 points."),
              ("dana", "2025-11-10 12:00", "Approved as this year's P1 baseline.")],
       commits=[("alice", "2025-11-05 09:00", "Class-conditioned sampler weights"),
                ("alice", "2025-11-09 17:00", "Run the comparison across all occlusion levels")])
    commit(V, "carol", "2025-11-20 10:00", "Harness: log per-class failure reasons")
    commit(V, "alice", "2025-12-02 14:00", "Hybrid sampler: tune the thin-part class threshold")
    commit(V, "carol", "2025-12-03 10:00", "Harness: add transparent-part scene set")
    commit(V, "carol", "2026-01-14 10:00", "Retry experiment scaffolding")
    commit(V, "alice", "2026-01-21 15:00", "Planner: transparent-part failure taxonomy")
    commit(V, "carol", "2026-02-09 10:00", "Harness: retry counters")
    issue("ACME-140", "Grasp retry policy under heavy occlusion", "Story", "alice", "2026-02-10 09:00", "carol",
          "Hypothesis: one re-scan after a failed grasp recovers most transparent-part failures at 60% occlusion.",
          labels=["research", "grasping"], resolved="2026-03-30 15:00",
          comments=[("carol", "2026-03-02 11:00", "One re-scan recovers 58% of failed transparent grasps; a second re-scan adds only 4 points."),
                    ("alice", "2026-03-15 14:00", "Policy: a single re-scan, then move to the next part.")])
    mr(V, 31, "carol", "2026-03-08 10:00", "Retry policy experiment",
       "A single re-scan after a failed grasp, measured on the transparent-part scene set (ACME-140).",
       ["planner/retry.py"], "feat/retry-policy", labels=["research"], merged="2026-03-25 16:00",
       commits=[("carol", "2026-03-08 09:30", "Re-scan after a failed grasp"),
                ("carol", "2026-03-18 14:00", "Measure recovery per re-scan count")])
    slack("research", "dana", "2026-03-26 16:00", "Weekly review: retry policy accepted; P1 trials are complete for the year.")
    mr(V, 37, "alice", "2026-05-12 09:00", "Occlusion results write-up and harness cleanup",
       "Consolidates this year's harness changes and exports the per-class result tables.",
       ["planner/harness.py", "docs/occlusion-results.md"], "chore/harness-cleanup", merged="2026-05-14 12:00",
       commits=[("alice", "2026-05-12 08:45", "Export per-class result tables")])
    commit(V, "alice", "2026-06-08 10:00", "Harness: export per-class tables for review")
    commit(V, "alice", "2026-07-20 10:00", "Planner: document retry policy parameters")

    # P2: Tactile Slip Detection (new project)
    issue("ACME-125", "Predict slip from tactile spectra within 30 ms", "Story", "bob", "2025-11-10 10:00", "bob",
          "Hypothesis: high-frequency spectral energy in the tactile signal rises before slip and can flag it within 30 ms, faster than force-threshold detection.",
          labels=["research", "tactile"], resolved="2026-01-08 15:00",
          comments=[("dana", "2025-11-18 09:00", "Please log latency for every run, not only the averages."),
                    ("bob", "2025-12-10 16:00", "The spectral predictor flags slip in 26 ms median on fresh sensors.")])
    mr(V, 24, "bob", "2025-11-18 10:00", "Tactile capture pipeline at 1 kHz",
       "Streams the fingertip sensor at 1 kHz with timestamps aligned to the gripper controller.",
       ["tactile/capture.py", "tactile/align.py"], "feat/tactile-capture", labels=["research"], merged="2025-11-25 15:00",
       commits=[("bob", "2025-11-18 09:30", "Stream the tactile sensor at 1 kHz"),
                ("bob", "2025-11-24 16:00", "Align tactile and controller clocks")])
    slack("dev", "bob", "2025-12-09 15:20",
          "Spectral slip predictor hits 30 ms on fresh sensors, but false positives climb after about 2 hours of use. Looks like sensor drift.",
          replies=[("alice", "2025-12-09 15:41", "Is it baseline drift or gain drift? A fixed threshold can't handle either."),
                   ("bob", "2025-12-09 15:58", "Trying a fixed threshold per sensor first to rule it out.")])
    mr(V, 26, "bob", "2025-12-16 10:00", "Fixed-threshold slip detector (abandoned)",
       "Per-sensor fixed thresholds. False positives still reached 22% after 3 hours as the baseline drifted, so this approach is abandoned in favour of adaptive compensation.",
       ["tactile/threshold.py"], "exp/fixed-threshold", labels=["research"],
       notes=[("alice", "2025-12-21 11:00", "Agree to drop it; the drift moves the baseline itself.")],
       commits=[("bob", "2025-12-16 09:30", "Per-sensor fixed slip threshold"),
                ("bob", "2025-12-18 17:00", "Measure false positives over 3-hour runs")])
    issue("ACME-133", "Adaptive baseline to compensate tactile drift", "Story", "bob", "2026-01-13 09:00", "bob",
          "Hypothesis: tracking the sensor baseline with a slow moving average keeps false positives under 5% over 6-hour runs without losing the 30 ms detection target.",
          labels=["research", "tactile"], resolved="2026-03-10 15:00",
          comments=[("alice", "2026-02-03 14:00", "The adaptive baseline keeps false positives at 4% over 6-hour runs."),
                    ("bob", "2026-02-24 10:00", "Detection latency rose to 29 ms median, still inside the target.")])
    mr(V, 28, "bob", "2026-02-01 10:00", "Adaptive baseline drift compensation",
       "A slow moving-average baseline per taxel, subtracted before spectral features (ACME-133).",
       ["tactile/baseline.py", "tactile/features.py"], "feat/adaptive-baseline", labels=["research"], merged="2026-02-20 14:00",
       notes=[("alice", "2026-02-05 10:00", "Window length looks like the main variable; try 30 s and 120 s.")],
       commits=[("bob", "2026-02-01 09:30", "Per-taxel moving-average baseline"),
                ("bob", "2026-02-12 15:00", "Compare 30 s and 120 s baseline windows")])
    mr(V, 33, "bob", "2026-04-14 10:00", "Slip detector latency profiling",
       "Profiles end-to-end detection latency on the gripper controller.",
       ["tactile/profile.py"], "feat/latency-profile", labels=["research"], merged="2026-04-22 12:00",
       notes=[("alice", "2026-04-20 15:00", "p95 latency is 27 ms on the controller build.")],
       commits=[("bob", "2026-04-14 09:30", "Profile detection latency on the controller")])
    slack("research", "dana", "2026-04-23 16:00", "Weekly review: tactile slip latency is within target on the controller.")
    commit(V, "bob", "2026-05-19 10:00", "Tactile: log drift statistics per session")
    slack("research", "dana", "2026-05-28 16:00", "Weekly review: drift on worn sensors is the open question for P2.")
    commit(V, "bob", "2026-06-16 10:00", "Tactile: retest baseline windows on worn sensors")
    slack("research", "dana", "2026-06-25 16:00", "Weekly review: P2 drift compensation holds on new sensors, not yet on worn ones.")
    commit(V, "bob", "2026-07-14 10:00", "Tactile: package the detector for the next gripper build")
    slack("research", "dana", "2026-07-23 16:00", "Year-end review: P1 and P2 results are summarized in the results docs.")

    # Routine work that is not SR&ED
    mr(W, 5, "bob", "2025-10-20 10:00", "Update pricing page copy", "Copy changes from marketing.", ["pages/pricing.tsx"],
       "content/pricing", labels=["website"], merged="2025-10-21 12:00", commits=[("bob", "2025-10-20 09:30", "Pricing page copy")])
    slack("general", "dana", "2025-10-22 09:00", "Customer demo for Northwind Logistics on Thursday; we need the latest grasping video.",
          replies=[("bob", "2025-10-22 09:20", "Recording it this afternoon.")])
    mr(W, 6, "dana", "2025-11-28 10:00", "Add customer logos to the home page", "Logo strip for the home page.",
       ["pages/index.tsx", "public/logos/northwind.svg"], "content/logos", labels=["website"], merged="2025-11-29 12:00",
       commits=[("dana", "2025-11-28 09:30", "Customer logo strip")])
    issue("ACME-150", "Website contact form returns 500", "Bug", "dana", "2026-03-01 09:00", "bob",
          "Submitting the contact form fails with a server error.", labels=["website"], resolved="2026-03-04 12:00",
          comments=[("bob", "2026-03-03 15:00", "Mail provider key expired; rotated it.")])
    mr(W, 7, "bob", "2026-03-03 10:00", "Contact form spam filter", "Adds a honeypot field.", ["pages/contact.tsx"],
       "fix/contact-spam", labels=["website"], merged="2026-03-03 16:00", commits=[("bob", "2026-03-03 09:30", "Honeypot field on contact form")])
    mr(W, 8, "bob", "2026-05-05 10:00", "Blog: grasping demo post", "Publishes the demo write-up.", ["content/blog/grasping-demo.md"],
       "content/blog", labels=["website"], merged="2026-05-06 12:00", commits=[("bob", "2026-05-05 09:30", "Grasping demo blog post")])
    for month in ("2025-11", "2025-12", "2026-01", "2026-02", "2026-04", "2026-06", "2026-07"):
        commit(W, "bob", f"{month}-03 11:00", "Website: copy updates")
    for month in ("2025-08", "2025-09", "2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"):
        commit(W, "renovate", f"{month}-06 03:00", "chore(deps): update dependency next to v15")


def jira_time(local: str) -> str:
    return t(local).strftime("%d/%b/%y %I:%M %p")


def write_jira(path: Path) -> None:
    header = ["Summary", "Issue key", "Issue id", "Issue Type", "Status", "Project key", "Assignee", "Reporter", "Created", "Resolved",
              "Labels", "Labels", "Description", "Comment", "Comment", "Comment"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        for i in sorted(ISSUES, key=lambda x: x["key"]):
            labels = (i["labels"] + ["", ""])[:2]
            comments = [f"{jira_time(when)};{PEOPLE[who][1]};{body}" for who, when, body in i["comments"]]
            writer.writerow([i["summary"], i["key"], str(10000 + int(i["key"].split("-")[1])), i["kind"],
                             "Done" if i["resolved"] else "In Progress", "ACME", PEOPLE[i["assignee"]][1], PEOPLE[i["reporter"]][1],
                             jira_time(i["created"]), jira_time(i["resolved"]) if i["resolved"] else "", *labels, i["description"],
                             *(comments + ["", "", ""])[:3]])


def dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def write_slack(folder: Path) -> None:
    dump(folder / "users.json", [{"id": sid, "name": handle, "real_name": name, "profile": {"email": email, "real_name": name}}
                                 for handle, name, email, sid in PEOPLE.values() if sid])
    dump(folder / "channels.json", [{"name": c} for c in sorted(SLACK)])
    for channel, messages in SLACK.items():
        by_day: dict[str, list[dict]] = {}
        for m in messages:
            day = datetime.fromtimestamp(float(m["ts"]), LOCAL).date().isoformat()
            by_day.setdefault(day, []).append(m)
        for day, msgs in by_day.items():
            dump(folder / channel / f"{day}.json", sorted(msgs, key=lambda m: m["ts"]))


def write_gitlab(raw: Path) -> list[Path]:
    files = []
    for project in sorted(MRS):
        path = raw / f"{project.replace('/', '__')}.json"
        dump(path, {"project": project, "merge_requests": sorted(MRS[project], key=lambda m: m["iid"]),
                    "commits": sorted(COMMITS[project], key=lambda c: c["authored_date"])})
        files.append(path)
    return files


def write_manifest(out: Path, files: list[Path]) -> None:
    entry = {
        "method": "api",
        "captured_at": "2026-08-02T00:00:00+00:00",
        "files": [{"path": str(f.relative_to(out)), "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "bytes": f.stat().st_size}
                  for f in sorted(files)],
        "counts": {"projects": len(MRS), "merge_requests": sum(len(v) for v in MRS.values()), "commits": sum(len(v) for v in COMMITS.values())},
        "date_range": ["2025-07-30", "2026-08-02"],
        "notes": ["pre-captured example data written by examples/acme/generate.py; the GitLab API was not called"],
    }
    dump(out / "evidence" / "raw" / "MANIFEST.json", {"sources": {"gitlab": entry}})


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(Path(__file__).resolve().parent))
    out = Path(p.parse_args(argv).out).resolve()
    year()
    for generated in (out / "exports" / "slack", out / "evidence" / "raw" / "gitlab"):
        if generated.exists():
            shutil.rmtree(generated)
    write_jira(out / "exports" / "jira.csv")
    write_slack(out / "exports" / "slack")
    write_manifest(out, write_gitlab(out / "evidence" / "raw" / "gitlab"))
    print(f"wrote example evidence under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
