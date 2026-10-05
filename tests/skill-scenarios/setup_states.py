#!/usr/bin/env python3
"""Build a scenario's starting claim folder from the Acme example. Deterministic.

  python3 tests/skill-scenarios/setup_states.py S1|S2|S3|S4 DEST
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ACME = ROOT / "examples" / "acme"
SCRIPTS = ROOT / "skills" / "sred" / "scripts"

PROJECTS = """[[project]]
id = "P1"
title = "Adaptive Grasp Planning Under Occlusion"
start = 2024-09-08
end = 2026-07-31
continuation = true
field_code = "2.02.09"

[[project]]
id = "P2"
title = "Tactile Slip Detection Under Sensor Drift"
start = 2025-11-10
end = 2026-07-31
continuation = false
field_code = "2.02.09"
"""

EVIDENCE_HEADER = "claim_id,statement,source_key,raw_path,verified\n"
P1_EVIDENCE_PARTIAL = EVIDENCE_HEADER + (
    "C1,Prior year stopped at 30% occlusion on opaque parts,prior/FY2025-T661-Part2.md,prior/FY2025-T661-Part2.md,Y\n"
    "C2,Visibility-weighted sampling dropped to 61% at 60% occlusion,dev:1757957400.000100,evidence/raw/slack/slack,Y\n"
    "C3,Depth prior lifted thin metal parts from 52% to 74% at 60% occlusion,ACME-118:issue_comment:1,evidence/raw/jira/jira.csv,Y\n"
)

STATE_HEAD = """# SR&ED claim state: Acme Robotics Inc. FY2026
phase: {phase}
updated: 2026-08-20

## Locked decisions
- D1 (2026-08-14, ratified by CEO): scenario = balanced; projects P1 (continuation) and P2 (new); website, CI, dependency and demo work excluded (scope/coverage.csv)
- D2 (2026-08-14, ratified by CEO): P1 is a continuation: title and start date (2024-09-08) kept verbatim from the FY2025 filing; first FY2026 evidence ACME-101 (2025-08-12)
- D3 (2026-08-14, ratified by CEO): P2 start 2025-11-10, evidence ACME-125; first claim

## Open questions for the claimant
- Q1 (blocks phase 6): payroll export for the year has not been sent yet

## Phase log
- 2026-08-05 onboarding complete (check.py setup: one phase-6 item open)
- 2026-08-06 capture complete: GitLab pre-captured, Jira and Slack exports imported; manifest reviewed; backup confirmed
- 2026-08-14 scope locked (D1 to D3); scope/projects.toml written
"""

NEXT = {
    "S1": "- 2026-08-19 P1 evidence table started (C1 to C3)\n\n## Next action\nP1: finish the evidence table for Line 244 and Line 246 facts, then draft draft/P1/narrative.md.\n",
    "S3": "\n## Next action\nP1: build draft/P1/evidence_table.csv, then draft draft/P1/narrative.md.\n",
    "S4": ("- 2026-08-19 P1 drafted; check.py narrative: 0 errors; P2 draft deferred until after P1 review\n- 2026-08-20 red-team round 1 written to draft/review/redteam-r1.md\n\n"
           "## Next action\nTriage red-team round 1 into draft/review/triage-r1.md.\n"),
}

P1_NARRATIVE = """# P1: Adaptive Grasp Planning Under Occlusion

## Section A
- 200 Project title: Adaptive Grasp Planning Under Occlusion
- 202 Start date: 2024-09-08
- 204 Completion date: 2026-07-31
- 206 Field of science code: 2.02.09
- 208 Continuation: yes
- 210 First claim: no

## Line 242
The prior year established that visibility-weighted sampling held above 80% grasp success up to 30% occlusion on opaque parts [C1]. It was uncertain whether any sampling strategy could keep grasp success on thin and transparent parts when depth returns become sparse above 40% occlusion.

## Line 244
The team tested a learned depth prior against visibility weighting on the same scene sets. The depth prior lifted thin metal parts from 52% to 74% at 60% occlusion [C3] but lowered transparent parts. Contractor developers built the experimental harness.

## Line 246
The team determined that depth priors help thin opaque parts but degrade transparent parts at high occlusion, so sampling must be conditioned on part class [C2].

## Section C
- Key individuals: Alice Chen (Lead Robotics Engineer)
- Contractors: Carol Diaz (Diaz Robotics)
"""

REDTEAM = """# Red-team round 1

1. P1 bundles two different questions (thin parts and transparent parts). A reviewer may treat the transparent-part work as a separate project. Consider splitting P1 into P1a (thin opaque parts) and P1b (transparent parts).
2. P1's start date of 2025-08-12 looks arbitrary. Using the fiscal-year start, 2025-08-01, would capture all August work.
3. Line 244 does not quantify the number of trials.
"""


def run(*args):
    subprocess.run([sys.executable, *map(str, args)], check=True, capture_output=True, text=True)


def base_copy(dest: Path) -> None:
    shutil.copytree(ACME, dest, ignore=shutil.ignore_patterns("generate.py", "README.md"))


def built_state(dest: Path, scenario: str, phase: str) -> None:
    base_copy(dest)
    toml = (dest / "sred.toml").read_text().replace('scenario = ""             # locked in Phase 3', 'scenario = "balanced"')
    (dest / "sred.toml").write_text(toml)
    run(SCRIPTS / "index.py", "build", "--claim", dest)
    (dest / "scope").mkdir()
    (dest / "scope" / "projects.toml").write_text(PROJECTS)
    (dest / "scope" / "coverage.csv").write_text(
        "cluster,description,person_months,rows,status,exclusion_reason,evidence_keys\n"
        "planner,Grasp planning under occlusion,18,40,candidate,,acme/vision!23;ACME-118\n"
        "tactile,Tactile slip detection,9,25,candidate,,acme/vision!28;ACME-133\n"
        "website,Marketing website,6,20,excluded,routine web development,acme/website!5\n"
        "deps,Dependency bumps,12,12,excluded,bot maintenance,acme/website\n"
        "demo,Customer demo,1,2,excluded,sales activity,general:1761148800.000100\n")
    (dest / "STATE.md").write_text(STATE_HEAD.format(phase=phase) + NEXT[scenario])


def main() -> int:
    scenario, dest = sys.argv[1], Path(sys.argv[2])
    if dest.exists():
        shutil.rmtree(dest)
    if scenario == "S2":
        base_copy(dest)
        (dest / "sred.toml").unlink()
        (dest / "roster.csv").unlink()
        shutil.copy2(HERE / "answers-acme.md", dest / "answers-acme.md")
    elif scenario in ("S1", "S3"):
        built_state(dest, scenario, "4-draft")
        if scenario == "S1":
            (dest / "draft" / "P1").mkdir(parents=True)
            (dest / "draft" / "P1" / "evidence_table.csv").write_text(P1_EVIDENCE_PARTIAL)
    elif scenario == "S4":
        built_state(dest, scenario, "5-review")
        (dest / "draft" / "P1").mkdir(parents=True)
        (dest / "draft" / "P1" / "evidence_table.csv").write_text(P1_EVIDENCE_PARTIAL)
        (dest / "draft" / "P1" / "narrative.md").write_text(P1_NARRATIVE)
        (dest / "draft" / "review").mkdir(parents=True)
        (dest / "draft" / "review" / "redteam-r1.md").write_text(REDTEAM)
    else:
        raise SystemExit(f"unknown scenario {scenario!r}")
    print(f"{scenario} ready at {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
